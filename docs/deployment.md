# Deployment Guide

This document describes the production deployment procedures for SilentSepsis services using Docker-based platforms (Render, Railway) and external managed dependencies (Supabase Postgres, Managed Redis).

Important: this repository is an academic prototype and is not validated for clinical use. Risk-tier thresholds and model outputs are not clinically validated and should not be used for medical decision-making or patient-facing production triage without separate clinical validation, regulatory review, and deployment safeguards.

The calibrated machine-learning predictor uses boundaries derived from its held-out calibrated-probability distribution and F1-optimal operating threshold: LOW `< 0.015`, MODERATE `0.015 <= score < 0.03150491842443488`, HIGH `0.03150491842443488 <= score < 0.20`, and CRITICAL `>= 0.20`. These are statistically/operationally derived boundaries for this model artifact, not clinically validated cutpoints. The rule-based predictor retains its separate legacy score boundaries.

---

## Architecture Overview

A complete production deployment requires three runtime services and two persistent datastores:

1. **SilentSepsis API (FastAPI)**: Serves client requests and routes.
2. **Celery Worker**: Executes patient risk evaluation tasks.
3. **Celery Beat**: Schedules evaluations periodically.
4. **PostgreSQL Database**: Persistent storage (e.g., Supabase).
5. **Redis**: Broker and backend for Celery task queuing.

---

## Pre-deploy checklist

Complete the following before the first production traffic:

1. Set `ENVIRONMENT=production` in the runtime environment.
2. Set real values for all secrets and connection strings in the hosting platform's environment variables:
   - `DATABASE_URL`
   - `REDIS_URL`
   - `SECRET_KEY`
   - `BOOTSTRAP_SECRET`
   - `CORS_ALLOWED_ORIGINS`
   - `ENABLE_METRICS`
3. Generate random secrets with a real random generator, not placeholders:
   ```bash
   python - <<'PY'
   import secrets
   print('SECRET_KEY=' + secrets.token_urlsafe(48))
   print('BOOTSTRAP_SECRET=' + secrets.token_urlsafe(48))
   PY
   ```
4. Set a strong PostgreSQL password for the managed database and use the real password in `DATABASE_URL` (do not reuse the dev default `postgres` or the docker-compose local test value).
5. Run database migrations against the production database before first traffic:
   ```bash
   alembic upgrade head
   ```
6. Bring up the API, worker, and scheduler only after the migration completes successfully.
7. Bootstrap the first admin account exactly once using the configured `X-Bootstrap-Secret` header and a real admin payload.
8. Confirm the bootstrap endpoint is locked afterwards: a second call with the same header should return `403` with `"Bootstrap has already been completed"`.
9. Confirm `CORS_ALLOWED_ORIGINS` matches the deployed frontend origin exactly, including scheme and hostname.
10. Confirm the frontend is served over HTTPS and `Strict-Transport-Security` is active.
11. Confirm `/metrics` is either private or disabled for public deploys.

---

## Security configuration notes

### CORS

`CORS_ALLOWED_ORIGINS` is env-driven in `app/core/config.py` via `parse_cors_origins()`, not hardcoded in a fixed string. It is read from environment as a comma-separated list and becomes `settings.cors_allowed_origins`.

Production value:

```text
CORS_ALLOWED_ORIGINS=https://app.example.com
```

For multiple frontends, use a comma-separated list:

```text
CORS_ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
```

Do not include `http://localhost` in production.

### HSTS / HTTPS activation

The HSTS header is set in [app/main.py](../app/main.py) only when the incoming request is HTTPS:

```python
if request.url.scheme == "https":
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
```

There is no separate `HSTS_*` env var controlling this. The relevant production condition is that the app must be reached over HTTPS. In practice, this means the platform must terminate TLS and present the original request as HTTPS to the app (or the reverse proxy must preserve the HTTPS scheme). `ENVIRONMENT=production` is still required operationally, but the actual HSTS activation is triggered by the request scheme, not by a dedicated env flag.

### `/metrics` exposure

The `/metrics` endpoint is unauthenticated and is gated only by `ENABLE_METRICS` in `app/core/config.py` and `app/main.py`.

- If the deploy is public, set `ENABLE_METRICS=false` to avoid exposing operational metrics to anyone who guesses or finds the URL.
- If the deploy is private or behind IP-based access control, `ENABLE_METRICS=true` is acceptable, but it should still be restricted at the ingress layer.

Recommendation for a public academic prototype: set `ENABLE_METRICS=false` unless the metrics endpoint is intentionally protected by a private network, VPN, or auth gateway.

---

## Prerequisites & Datastores Setup

Before deploying the runtime services, configure the managed database and cache instances.

### 1. PostgreSQL Setup (Supabase / RDS)
1. Create a PostgreSQL project on [Supabase](https://supabase.com) or your cloud provider of choice.
2. Under project settings, retrieve the Connection String (URI format).
3. Update the credentials in your production variables (e.g. `postgresql://postgres.[username]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres`).
4. **CRITICAL**: Before starting the API, Celery worker, or Beat containers, you must run the database migrations:
   ```bash
   alembic upgrade head
   ```
   *Tip: You can run this command locally with the production connection string or configure your hosting platform to execute it as a release phase command.*

### 2. Managed Redis Setup (Upstash / Redis Labs)
1. Provision a Redis database (e.g., standard replica/managed Redis on Upstash or Redis Labs).
2. Retrieve the connection URL.
3. Note the connection URI: `redis://:[password]@[endpoint]:[port]/0`.

---

## Deployment Steps

All runtime services are built from the same unified `Dockerfile` located in the root of the repository.

### Option A: Railway Deployment

Railway supports deploying multiple services from a single repository using different start commands.

1. **API Service**:
   - Create a service pointing to your GitHub repository.
   - Railway will auto-detect the `Dockerfile`.
   - Set the Custom Start Command to: `uvicorn app.main:app --host 0.0.0.0 --port 8000` (or leave empty to default to the Dockerfile CMD).
   - Under Settings, map port `8000`.

2. **Celery Worker**:
   - Create a second service from the same repository.
   - Set the Custom Start Command to: `celery -A app.tasks.celery_app worker --loglevel=info`
   - Disable public networking/domain mappings for this service.

3. **Celery Beat**:
   - Create a third service from the same repository.
   - Set the Custom Start Command to: `celery -A app.tasks.celery_app beat --loglevel=info --schedule /tmp/celerybeat-schedule`
   - Disable public networking/domain mappings.

---

### Option B: Render Deployment

Render uses separate Web Services and Background Workers.

1. **API Service (Web Service)**:
   - Create a **Web Service** linked to your repository.
   - Set **Environment** to `Docker`.
   - Set **Port** to `8000`.
   - Set the Build Command and Start Command to default.

2. **Celery Worker (Background Worker)**:
   - Create a **Background Worker** linked to your repository.
   - Set **Environment** to `Docker`.
   - Set the Docker Command to: `celery -A app.tasks.celery_app worker --loglevel=info`

3. **Celery Beat (Background Worker)**:
   - Create a **Background Worker** linked to your repository.
   - Set **Environment** to `Docker`.
   - Set the Docker Command to: `celery -A app.tasks.celery_app beat --loglevel=info --schedule /tmp/celerybeat-schedule`

---

## Required Production Environment Variables

Ensure the following variables are set in your platform's environment/shared variables group:

| Variable | Description / Value | Reference |
|---|---|---|
| `DATABASE_URL` | Production PostgreSQL connection string (with pooled connection if using Supabase) | `.env.example` |
| `REDIS_URL` | Production Redis connection string | `.env.example` |
| `SECRET_KEY` | Long, cryptographically secure random string (used for JWT generation) | `.env.example` |
| `ALGORITHM` | Encryption algorithm (e.g. `HS256`) | `.env.example` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiration timeframe (e.g., `30` minutes) | `.env.example` |
| `BOOTSTRAP_SECRET` | Header secret string to enable admin user bootstrapping | `.env.example` |
| `RISK_EVALUATION_INTERVAL_MINUTES` | Frequency of Celery Beat risk calculations (e.g., `5` minutes) | `.env.example` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed origins (e.g. `https://app.silentsepsis.com`) | `.env.example` |
| `LOGIN_RATE_LIMIT` | Rate limit for auth endpoints (e.g., `5/minute`) | `.env.example` |
| `BOOTSTRAP_RATE_LIMIT` | Rate limit for admin bootstrapping (e.g., `3/minute`) | `.env.example` |
| `DEFAULT_RATE_LIMIT` | Default fallback rate limit (e.g., `100/minute`) | `.env.example` |
| `ENVIRONMENT` | Run environment set to `production` | `.env.example` |
| `ENABLE_METRICS` | Gating for metrics collection (`true`/`false`) | `.env.example` |

Also ensure the database-side service credentials are set in the container environment, especially:

| Variable | Example purpose | Production requirement |
|---|---|---|
| `POSTGRES_DB` | PostgreSQL database name | Must match your production DB name |
| `POSTGRES_USER` | Superuser or application database user | Must be a managed credential, not `postgres` in public deployments |
| `POSTGRES_PASSWORD` | Database password | Must be a strong random secret, not a test default |

---

## Bootstrap flow and lock-down

The bootstrap endpoint enforces a shared secret header and will reject invalid secrets before creating the first admin user. The service then refuses any further bootstrap once an Admin role user exists.

Example bootstrap command:

```bash
curl -X POST https://api.example.com/auth/bootstrap \
  -H 'X-Bootstrap-Secret: <BOOTSTRAP_SECRET>' \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "admin@example.com",
    "staff_id": "ADM-001",
    "full_name": "Initial Administrator",
    "password": "<strong-admin-password>",
    "role_name": "Admin"
  }'
```

The follow-up check should be:

```bash
curl -i -X POST https://api.example.com/auth/bootstrap \
  -H 'X-Bootstrap-Secret: <BOOTSTRAP_SECRET>' \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "admin2@example.com",
    "staff_id": "ADM-002",
    "full_name": "Second Administrator",
    "password": "<another-strong-password>",
    "role_name": "Admin"
  }'
```

Expected: second call returns `403` with `Bootstrap has already been completed`.

---

## Production operational caution

This is an academic prototype, not a clinically validated system. Its model thresholds and alert tiers are exploratory and should not be relied on for acute clinical triage or patient care decisions without additional clinical review and validation. The deployment context is best treated as a portfolio or academic demonstration environment, not a production-grade clinical monitor.

---

## Known configuration gap to watch

The app relies on a default `Settings` object with dev values if environment variables are not set. That is acceptable for local development but dangerous in production because values like `SECRET_KEY`, `BOOTSTRAP_SECRET`, and `POSTGRES_PASSWORD` are only safe when environment variables override them. In addition, HSTS is triggered only when the incoming request scheme is HTTPS; if a reverse proxy terminates TLS without preserving the original scheme, the header will not be emitted even in production. Review the hosting platform's proxy and HTTPS behavior before launch.
