# SilentSepsis API

[![CI](https://github.com/Ramyasai07/silentsepsis/actions/workflows/ci.yml/badge.svg)](https://github.com/Ramyasai07/silentsepsis/actions/workflows/ci.yml)

SilentSepsis is a real-time sepsis risk monitoring backend. It coordinates patient
telemetry updates, ward occupancy statistics, automated predictive alerting, and
audit log histories.

---

## Backend Testing

The backend test suite is powered by `pytest`. Tests run inside the API container
against the database service configured in `docker-compose.yml`.

### How to Run Tests

Ensure the docker services are running:
```bash
docker compose up -d
```

Wait for all 5 services to pass their healthchecks:
```bash
docker compose ps
```

Run the pytest suite inside the API container:
```bash
docker compose exec api pytest
```

### Test Database Configuration & Isolation

Tests run against `silentsepsis_test`, never `silentsepsis`. The safety guard in
`app/tests/conftest.py` refuses to start pytest unless `TEST_DATABASE_URL` names
a database ending in `_test`. Alembic migrations run against that same URL.

The Docker Compose Postgres service hosts both databases on one Postgres instance.
On a fresh volume, `docker/postgres/init-test-db.sql` creates `silentsepsis_test`
automatically. If the existing `postgres_data` volume predates this script, create
the database once with:

```bash
docker compose exec db psql -U postgres -d postgres -c "CREATE DATABASE silentsepsis_test;"
```

Then run migrations and tests in the API container:

```bash
docker compose exec -e DATABASE_URL=postgresql://postgres:postgres@db:5432/silentsepsis_test api alembic upgrade head
docker compose exec api pytest
```

`DATABASE_URL` remains the application database connection. `TEST_DATABASE_URL` is
the test-only connection and must never point to `silentsepsis`.

---

## Academic prototype notice

This project is an academic/portfolio prototype and is not validated for clinical use. Risk-tier thresholds, model scores, and alert logic are exploratory and should not be treated as clinically validated recommendations for patient care or medical decision-making.

The calibrated machine-learning predictor uses statistically informed operating boundaries based on its held-out calibrated-probability distribution and F1-optimal threshold. The 0.20 HIGH/CRITICAL boundary is an operational separation for this model artifact. These boundaries are not clinically validated cutpoints.

---

## Infrastructure Endpoints

| Endpoint | Auth | Description |
|---|---|---|
| `GET /health` | None | Liveness probe — always 200, no DB/Redis calls |
| `GET /ready` | None | Readiness probe — checks DB + Redis connectivity |
| `GET /metrics` | None | Prometheus metrics (gated by `ENABLE_METRICS`) |

---

## Docker Compose Services

| Service | Description |
|---|---|
| `api` | FastAPI application (uvicorn) |
| `worker` | Celery worker for async tasks |
| `beat` | Celery beat scheduler |
| `db` | PostgreSQL 16 |
| `redis` | Redis 7 |

All services have `restart: unless-stopped` and health checks configured.

---

## Deployment

See [docs/deployment.md](docs/deployment.md) for Render/Railway deployment steps,
Supabase Postgres setup, and required production environment variables.

## SQL Query Optimization

See [docs/query-optimization.md](docs/query-optimization.md) for before/after
`EXPLAIN ANALYZE` results and percentage improvement from the `alerts.created_at`
index added in Commit 12.
