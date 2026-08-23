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

- **Connection**: Tests run against the database URL configured in the `DATABASE_URL`
  environment variable inside the container (defaulting to the shared `silentsepsis` database).
- **Schema Migration**: On session start, `alembic` migrations are automatically executed
  via a session-scoped fixture to ensure the schema is up-to-date with `head`.
- **Data Isolation**: Since tests share the database, data isolation between tests is
  maintained by table-cleaning fixtures (e.g. `clean_data` or `clean_users` with
  `autouse=True`) in each test file. These fixtures perform `DELETE` queries on all model
  tables before and after each test run.
- **Environment Variables**:
  - `DATABASE_URL`: Connection string for PostgreSQL database.
  - `REDIS_URL`: Connection string for Redis instance.
  - `BOOTSTRAP_SECRET`: Secret header key for admin bootstrapping.
  - `ENABLE_METRICS`: Set to `true` to enable the `/metrics` endpoint.

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
