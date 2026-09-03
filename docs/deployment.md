# Deployment Guide

This document describes the production deployment procedures for SilentSepsis services using Docker-based platforms (Render, Railway) and external managed dependencies (Supabase Postgres, Managed Redis).

---

## Architecture Overview

A complete production deployment requires three runtime services and two persistent datastores:

1. **SilentSepsis API (FastAPI)**: Serves client requests and routes.
2. **Celery Worker**: Executes patient risk evaluation tasks.
3. **Celery Beat**: Schedules evaluations periodically.
4. **PostgreSQL Database**: Persistent storage (e.g., Supabase).
5. **Redis**: Broker and backend for Celery task queuing.

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
