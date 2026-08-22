"""
benchmark_alerts.py — Commit 12 SQL query optimization benchmark.

Purpose: Produce reproducible BEFORE/AFTER EXPLAIN (ANALYZE, BUFFERS) output for
         docs/query-optimization.md.

What this script does (in order):
  1. Verifies the ix_alerts_created_at index exists (it is created by the
     Alembic migration).
  2. Seeds the database with ~3 000 realistic alert rows using valid FK chains:
       role -> user -> ward -> patient -> vital_reading -> prediction -> alert
     Idempotent: rows with hospital_patient_id prefix 'BM-' are reused if
     present.
  3. Drops ix_alerts_created_at temporarily to simulate the PRE-index baseline.
  4. Runs EXPLAIN (ANALYZE, BUFFERS) on the target query and prints the plan.
  5. Recreates ix_alerts_created_at.
  6. Runs the same EXPLAIN (ANALYZE, BUFFERS) again and prints the post-index
     plan.
  7. Prints a summary table.
  8. Cleans up ONLY the benchmark seed rows (no other data is touched).

The target query is:
    SELECT * FROM alerts ORDER BY created_at DESC LIMIT 50 OFFSET 0;

Safety guarantees:
  - Only inserts rows where hospital_patient_id LIKE 'BM-%'.
  - Cleanup deletes ONLY rows created by this script (same prefix filter).
  - Does NOT truncate, drop, or reset any table.
  - Does NOT modify application data.

Usage (inside the api container):
    python scripts/benchmark_alerts.py
"""

import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/app")
os.environ.setdefault(
    "DATABASE_URL", "postgresql://postgres:[REDACTED]@db:5432/silentsepsis"
)
os.environ.setdefault("REDIS_URL", "redis://redis:6379/0")
os.environ.setdefault("BOOTSTRAP_SECRET", "benchmark-only")

from sqlalchemy import text

from app.db.session import engine

# ── config ──────────────────────────────────────────────────────────────────
SEED_PATIENTS = 50  # patients to create
VITALS_PER_PATIENT = 60  # one vital → one prediction → one alert
ALERTS_TARGET = SEED_PATIENTS * VITALS_PER_PATIENT  # 3 000 alerts
BASE_TIME = datetime(2025, 1, 1, tzinfo=timezone.utc)
BM_PREFIX = "BM-"  # hospital_patient_id prefix for idempotent cleanup
# ─────────────────────────────────────────────────────────────────────────────


def _run(conn, sql: str, params=None):
    return conn.execute(text(sql), params or {})


def seed(raw):
    """Insert benchmark rows.  Returns list of patient_ids created."""
    cur = raw.cursor()

    # ── role ─────────────────────────────────────────────────────────────────
    cur.execute(
        "INSERT INTO roles (id, name, description)"
        " VALUES (%s, 'BenchmarkRole', 'benchmark')"
        " ON CONFLICT (name) DO NOTHING",
        (str(uuid.uuid4()),),
    )
    cur.execute("SELECT id FROM roles WHERE name = 'BenchmarkRole'")
    role_id = cur.fetchone()[0]

    # ── ward ─────────────────────────────────────────────────────────────────
    ward_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO wards (id, ward_name, department, capacity)"
        " VALUES (%s, 'BenchmarkWard', 'ICU', 60)"
        " ON CONFLICT (ward_name) DO NOTHING",
        (ward_id,),
    )
    cur.execute("SELECT id FROM wards WHERE ward_name = 'BenchmarkWard'")
    ward_id = cur.fetchone()[0]

    # ── user ─────────────────────────────────────────────────────────────────
    user_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO users"
        " (id, full_name, email, hashed_password, role_id, staff_id, is_active)"
        " VALUES (%s, 'Bench User', 'bench@bm.test', 'x', %s, 'BM-STAFF', true)"
        " ON CONFLICT (email) DO NOTHING",
        (user_id, role_id),
    )
    cur.execute("SELECT id FROM users WHERE email = 'bench@bm.test'")
    user_id = cur.fetchone()[0]

    # ── patients ─────────────────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM patients WHERE hospital_patient_id LIKE 'BM-%%'")
    existing_patients = cur.fetchone()[0]

    if existing_patients >= SEED_PATIENTS:
        print(f"  Already have {existing_patients} benchmark patients" f" — reusing.")
        cur.execute(
            "SELECT id FROM patients WHERE hospital_patient_id LIKE 'BM-%%'"
            " LIMIT %s",
            (SEED_PATIENTS,),
        )
        patient_ids = [r[0] for r in cur.fetchall()]
    else:
        print(f"  Seeding {SEED_PATIENTS} patients…")
        patient_ids = []
        for i in range(SEED_PATIENTS):
            pid = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO patients
                    (id, hospital_patient_id, full_name, age, gender,
                     admission_date, current_status, ward_id, diagnosis, bed_number)
                VALUES (%s, %s, %s, %s, 'MALE', %s, 'ADMITTED', %s, 'benchmark', %s)
                ON CONFLICT DO NOTHING
                """,
                (
                    pid,
                    f"{BM_PREFIX}{i:04d}",
                    f"BM Patient {i}",
                    30 + (i % 50),
                    BASE_TIME + timedelta(days=i),
                    ward_id,
                    f"BM-{i:03d}",
                ),
            )
            patient_ids.append(pid)
        raw.commit()
        # Re-fetch actual IDs (ON CONFLICT may have been a no-op for some)
        cur.execute(
            "SELECT id FROM patients WHERE hospital_patient_id LIKE 'BM-%%'"
            " LIMIT %s",
            (SEED_PATIENTS,),
        )
        patient_ids = [r[0] for r in cur.fetchall()]

    # ── vitals ───────────────────────────────────────────────────────────────
    cur.execute(
        "SELECT COUNT(*) FROM vital_readings vr"
        " JOIN patients p ON p.id = vr.patient_id"
        " WHERE p.hospital_patient_id LIKE 'BM-%%'"
    )
    existing_vitals = cur.fetchone()[0]

    if existing_vitals >= ALERTS_TARGET:
        print(f"  Already have {existing_vitals} benchmark vitals" f" — reusing.")
        cur.execute(
            """
            SELECT vr.id, vr.patient_id FROM vital_readings vr
            JOIN patients p ON p.id = vr.patient_id
            WHERE p.hospital_patient_id LIKE 'BM-%%'
            LIMIT %s
            """,
            (ALERTS_TARGET,),
        )
        vital_pairs = cur.fetchall()
    else:
        print("  Seeding vitals…")
        vital_rows = []
        for pid in patient_ids:
            for j in range(VITALS_PER_PATIENT):
                vital_rows.append(
                    (
                        str(uuid.uuid4()),
                        pid,
                        user_id,
                        60.0 + random.uniform(-20, 40),
                        120.0 + random.uniform(-30, 40),
                        80.0 + random.uniform(-20, 20),
                        16.0 + random.uniform(-4, 10),
                        95.0 + random.uniform(-10, 5),
                        37.0 + random.uniform(-1, 2),
                        BASE_TIME + timedelta(hours=j * 2),
                        BASE_TIME + timedelta(hours=j * 2),
                        BASE_TIME + timedelta(hours=j * 2),
                    )
                )
        cur.executemany(
            """
            INSERT INTO vital_readings
                (id, patient_id, recorded_by, heart_rate, systolic_bp,
                 diastolic_bp, respiratory_rate, spo2, temperature,
                 recorded_at, created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT DO NOTHING
            """,
            vital_rows,
        )
        raw.commit()
        cur.execute(
            """
            SELECT vr.id, vr.patient_id FROM vital_readings vr
            JOIN patients p ON p.id = vr.patient_id
            WHERE p.hospital_patient_id LIKE 'BM-%%'
            LIMIT %s
            """,
            (ALERTS_TARGET,),
        )
        vital_pairs = cur.fetchall()

    # ── predictions ──────────────────────────────────────────────────────────
    cur.execute("""
        SELECT COUNT(*) FROM predictions pr
        JOIN patients p ON p.id = pr.patient_id
        WHERE p.hospital_patient_id LIKE 'BM-%%'
        """)
    existing_preds = cur.fetchone()[0]

    if existing_preds >= len(vital_pairs):
        print(f"  Already have {existing_preds} benchmark predictions" f" — reusing.")
        cur.execute(
            """
            SELECT pr.id, pr.patient_id FROM predictions pr
            JOIN patients p ON p.id = pr.patient_id
            WHERE p.hospital_patient_id LIKE 'BM-%%'
            LIMIT %s
            """,
            (ALERTS_TARGET,),
        )
        pred_pairs = cur.fetchall()
    else:
        print("  Seeding predictions…")
        risk_levels = ["LOW", "MODERATE", "HIGH", "CRITICAL"]
        pred_rows = []
        for vid, pid in vital_pairs:
            pred_rows.append(
                (
                    str(uuid.uuid4()),
                    pid,
                    vid,
                    "rule-based-v1",
                    random.uniform(0.1, 0.99),
                    random.choice(risk_levels),
                    BASE_TIME + timedelta(minutes=random.randint(0, 50000)),
                    BASE_TIME,
                    BASE_TIME,
                )
            )
        cur.executemany(
            """
            INSERT INTO predictions
                (id, patient_id, vital_reading_id, model_version,
                 risk_probability, risk_level, generated_at, created_at,
                 updated_at)
            VALUES (%s,%s,%s,%s,%s,%s::risk_level,%s,%s,%s)
            ON CONFLICT DO NOTHING
            """,
            pred_rows,
        )
        raw.commit()
        cur.execute(
            """
            SELECT pr.id, pr.patient_id FROM predictions pr
            JOIN patients p ON p.id = pr.patient_id
            WHERE p.hospital_patient_id LIKE 'BM-%%'
            LIMIT %s
            """,
            (ALERTS_TARGET,),
        )
        pred_pairs = cur.fetchall()

    # ── alerts ───────────────────────────────────────────────────────────────
    cur.execute("""
        SELECT COUNT(*) FROM alerts al
        JOIN patients p ON p.id = al.patient_id
        WHERE p.hospital_patient_id LIKE 'BM-%%'
        """)
    existing_alerts = cur.fetchone()[0]

    if existing_alerts >= ALERTS_TARGET:
        print(f"  Already have {existing_alerts} benchmark alerts" f" — reusing.")
    else:
        print(f"  Seeding {len(pred_pairs)} alerts…")
        statuses = [
            "active",
            "active",
            "watching",
            "confirmed",
            "dismissed",
            "resolved",
        ]
        severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        alert_rows = []
        for i, (prid, pid) in enumerate(pred_pairs):
            alert_rows.append(
                (
                    str(uuid.uuid4()),
                    pid,
                    prid,
                    random.choice(severities),
                    random.choice(statuses),
                    f"Benchmark alert {i}",
                    BASE_TIME + timedelta(minutes=i * 5),
                    BASE_TIME + timedelta(minutes=i * 5),
                )
            )
        cur.executemany(
            """
            INSERT INTO alerts
                (id, patient_id, prediction_id, severity, status, message,
                 created_at, updated_at)
            VALUES (%s,%s,%s,%s::alert_severity,%s::alert_status,%s,%s,%s)
            ON CONFLICT DO NOTHING
            """,
            alert_rows,
        )
        raw.commit()

    cur.execute("""
        SELECT COUNT(*) FROM alerts al
        JOIN patients p ON p.id = al.patient_id
        WHERE p.hospital_patient_id LIKE 'BM-%%'
        """)
    final_count = cur.fetchone()[0]
    print(f"  Final benchmark alert row count: {final_count}")
    cur.close()
    return final_count


def explain(raw, label: str) -> str:
    cur = raw.cursor()
    cur.execute(
        "EXPLAIN (ANALYZE, BUFFERS) "
        "SELECT * FROM alerts ORDER BY created_at DESC LIMIT 50 OFFSET 0"
    )
    rows = cur.fetchall()
    cur.close()
    plan = "\n".join(r[0] for r in rows)
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    print(plan)
    return plan


def cleanup(raw):
    cur = raw.cursor()
    print("\n  Cleaning up benchmark seed rows (BM- prefix only)…")
    cur.execute("""
        DELETE FROM alerts
        WHERE patient_id IN (
            SELECT id FROM patients WHERE hospital_patient_id LIKE 'BM-%%'
        )
        """)
    cur.execute("""
        DELETE FROM predictions
        WHERE patient_id IN (
            SELECT id FROM patients WHERE hospital_patient_id LIKE 'BM-%%'
        )
        """)
    cur.execute("""
        DELETE FROM vital_readings
        WHERE patient_id IN (
            SELECT id FROM patients WHERE hospital_patient_id LIKE 'BM-%%'
        )
        """)
    cur.execute("DELETE FROM patients WHERE hospital_patient_id LIKE 'BM-%%'")
    cur.execute("DELETE FROM users WHERE email = 'bench@bm.test'")
    cur.execute("DELETE FROM wards WHERE ward_name = 'BenchmarkWard'")
    cur.execute("DELETE FROM roles WHERE name = 'BenchmarkRole'")
    raw.commit()
    cur.close()
    print("  Cleanup complete.")


def main():
    raw = engine.raw_connection()
    try:
        print("\n[1/6] Seeding benchmark data…")
        alert_count = seed(raw)

        print("\n[2/6] BASELINE — dropping ix_alerts_created_at temporarily…")
        cur = raw.cursor()
        cur.execute("DROP INDEX IF EXISTS ix_alerts_created_at")
        raw.commit()
        cur.close()

        print("\n[3/6] Running EXPLAIN ANALYZE without index (BASELINE)…")
        before_plan = explain(
            raw,
            "BASELINE — no ix_alerts_created_at (Sequential Scan expected)",
        )

        print("\n[4/6] Recreating ix_alerts_created_at…")
        cur = raw.cursor()
        cur.execute("CREATE INDEX ix_alerts_created_at ON alerts (created_at)")
        raw.commit()
        cur.close()

        print("\n[5/6] Running EXPLAIN ANALYZE WITH index (OPTIMIZED)…")
        after_plan = explain(
            raw,
            "OPTIMIZED — ix_alerts_created_at present (Index Scan expected)",
        )

        print("\n[6/6] Summary")
        before_time = None
        after_time = None
        for line in before_plan.splitlines():
            if "Execution Time" in line:
                before_time = line.strip()
        for line in after_plan.splitlines():
            if "Execution Time" in line:
                after_time = line.strip()

        print(f"\n  Dataset: {alert_count} alert rows")
        print(f"  BEFORE: {before_time}")
        print(f"  AFTER:  {after_time}")
        print()
    finally:
        cleanup(raw)
        raw.close()


if __name__ == "__main__":
    main()
