# SQL Query Optimization Report — Commit 12

This document records the performance investigation, implementation, and verified
benchmark results for the `alerts.created_at` index added in Commit 12.

All numbers in this document were obtained from a real PostgreSQL execution inside
the running Docker Compose stack.  The benchmark script that produced them is
[`scripts/benchmark_alerts.py`](../scripts/benchmark_alerts.py).

---

## Target Query

The global alert-listing query issued by `get_alerts()` in
`app/services/alert_service.py` when no filters are supplied:

```sql
SELECT * FROM alerts
ORDER BY created_at DESC
LIMIT 50 OFFSET 0;
```

This is the query executed whenever a clinician opens the alerts dashboard without
filtering by patient or ward.

---

## Benchmark Environment

| Item | Value |
|---|---|
| PostgreSQL version | 16 (Docker image `postgres:16`) |
| Alert rows seeded | **3 000** |
| FK chain | `role → user → ward → patient → vital_reading → prediction → alert` |
| Seed script | `scripts/benchmark_alerts.py` |
| Cleanup | Full cleanup of benchmark rows after measurement |

---

## BEFORE — Without `ix_alerts_created_at`

Index was removed by downgrading Alembic from `1c10c0e5cde9` to `20260809_0005`
before capturing this baseline plan.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM alerts ORDER BY created_at DESC LIMIT 50 OFFSET 0;
```

```text
Limit  (cost=179.66..179.78 rows=50 width=220) (actual time=1.032..1.039 rows=50 loops=1)
  Buffers: shared hit=53
  ->  Sort  (cost=179.66..187.16 rows=3000 width=220) (actual time=1.030..1.033 rows=50 loops=1)
        Sort Key: created_at DESC
        Sort Method: top-N heapsort  Memory: 38kB
        Buffers: shared hit=53
        ->  Seq Scan on alerts  (cost=0.00..80.00 rows=3000 width=220) (actual time=0.007..0.324 rows=3000 loops=1)
              Buffers: shared hit=50
Planning:
  Buffers: shared hit=262 dirtied=1
Planning Time: 0.621 ms
Execution Time: 1.090 ms
```

**Key observations (BEFORE):**

- PostgreSQL chose a full **Sequential Scan** across all 3 000 alert rows.
- Results were sorted using an in-memory **top-N heapsort** (38 kB RAM).
- **53 shared buffer blocks** were accessed.
- **Execution Time: 1.090 ms**

---

## Implementation — Alembic Migration

Migration `1c10c0e5cde9_add_index_alerts_created_at.py` adds a standard B-tree index:

```python
def upgrade() -> None:
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_alerts_created_at", table_name="alerts")
```

The index is also declared in the SQLAlchemy model
[`app/models/alert.py`](../app/models/alert.py):

```python
__table_args__ = (
    Index("ix_alerts_patient_status_created_at", "patient_id", "status", "created_at"),
    Index("ix_alerts_created_at", "created_at"),
)
```

---

## AFTER — With `ix_alerts_created_at`

Index was added back by re-running `alembic upgrade head` (migration
`1c10c0e5cde9`) before capturing this optimized plan.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM alerts ORDER BY created_at DESC LIMIT 50 OFFSET 0;
```

```text
Limit  (cost=0.28..2.65 rows=50 width=220) (actual time=0.038..0.050 rows=50 loops=1)
  Buffers: shared hit=2 read=2
  ->  Index Scan Backward using ix_alerts_created_at on alerts  (cost=0.28..142.28 rows=3000 width=220) (actual time=0.037..0.044 rows=50 loops=1)
        Buffers: shared hit=2 read=2
Planning:
  Buffers: shared hit=260 read=1 dirtied=2
Planning Time: 0.790 ms
Execution Time: 0.107 ms
```

**Key observations (AFTER):**

- PostgreSQL uses an **Index Scan Backward** on `ix_alerts_created_at`.  The index
  stores rows in ascending `created_at` order, so a backward scan yields them in
  descending order without a separate sort step.
- **Sort step is completely eliminated** — 0 kB RAM for sorting.
- Only **4 shared buffer blocks** (2 hit, 2 read) were accessed instead of 53.
- **Execution Time: 0.107 ms**

---

## Measured Results Summary

| Metric | BEFORE (no index) | AFTER (with index) | Change |
|---|---|---|---|
| **Scan type** | Sequential Scan | Index Scan Backward | Optimized |
| **Sort step** | top-N heapsort (38 kB) | None (eliminated) | 100% eliminated |
| **Buffer blocks accessed** | 53 | 4 | −92.5% |
| **Execution Time** | 1.090 ms | 0.107 ms | **−90.1834862385321% (~10.1869158878505× faster)** |
| **Planning Time** | 0.621 ms | 0.790 ms | +0.169 ms |

### Why the index helps here

The query has no `WHERE` predicate — it fetches the 50 most-recent rows globally.
PostgreSQL can satisfy this entirely by walking the B-tree leaf pages in reverse
order, reading exactly as many pages as needed to return 50 rows.  Without the
index, PostgreSQL must read every row in the table into memory before it can sort
and discard most of them.

### Scaling behaviour

The index scan reads a number of pages proportional to the 50 rows requested, not
to the total table size.  The sequential scan reads a number of pages proportional
to the total table size.  As the `alerts` table grows with operational data the gap
between the two plans will widen further.

The index does not make the query *infinitely* scalable — very large tables may
still require careful pagination tuning — but for the dashboard's default first-page
query it provides a stable, predictable execution path.

---

## Reproducing This Benchmark

```bash
# Ensure the stack is running and migrations are applied:
docker compose up -d
docker compose exec api alembic upgrade head

# Run the benchmark (seeds, measures, cleans up automatically):
docker compose exec api python scripts/benchmark_alerts.py
```

The script creates 3 000 alert rows with valid FK relationships, captures
EXPLAIN ANALYZE plans before and after the index, prints both plans, then
deletes all benchmark rows automatically.  It does not touch application data.
