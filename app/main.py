import logging
import time

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.limiter import limiter
from app.core.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
)

# ---------------------------------------------------------------------------
# Structured logging setup (structlog → stdlib bridge)
# ---------------------------------------------------------------------------

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Ensure the stdlib root logger (used by existing modules) is set to INFO
logging.basicConfig(level=logging.INFO)

_log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# OpenAPI tag metadata
# ---------------------------------------------------------------------------

tags_metadata = [
    {
        "name": "auth",
        "description": (
            "Authentication and user management operations "
            "including admin bootstrapping."
        ),
    },
    {
        "name": "patients",
        "description": "Patient registration, profiles, and clinical watchlists.",
    },
    {
        "name": "wards",
        "description": "Ward configuration, beds mapping, and occupancy management.",
    },
    {
        "name": "vitals",
        "description": "Recording and monitoring of patient physiological vitals.",
    },
    {
        "name": "predictions",
        "description": (
            "Sepsis risk evaluations, prediction history, and explanation features."
        ),
    },
    {
        "name": "alerts",
        "description": (
            "Real-time sepsis alerts, acknowledgements, "
            "resolutions, and lifecycle management."
        ),
    },
    {
        "name": "feedback",
        "description": "Clinician feedback submission and annotations on model alerts.",
    },
    {
        "name": "audit-logs",
        "description": (
            "Auditing and tracking of critical clinician actions and system changes."
        ),
    },
    {
        "name": "analytics",
        "description": (
            "Sepsis incidence analytics, ward statistics, "
            "and model performance metrics."
        ),
    },
    {
        "name": "tasks/admin",
        "description": (
            "Administrative tasks, celery worker diagnostics, and maintenance routines."
        ),
    },
]

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SilentSepsis API",
    description=(
        "SilentSepsis API provides the backend clinical services and real-time sepsis "
        "risk monitoring capabilities. It coordinates patient telemetry updates, ward "
        "occupancy statistics, automated predictive alerting, and audit log histories."
    ),
    version="0.1.0",
    openapi_tags=tags_metadata,
)

# CORS Middleware (dynamic allowed origins from settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiter setup
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded: please try again later."},
    )


# ---------------------------------------------------------------------------
# Security Headers Middleware
# ---------------------------------------------------------------------------


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


# ---------------------------------------------------------------------------
# Request Logging + Prometheus Middleware
# ---------------------------------------------------------------------------

# Paths that are exempt from rate limiting and produce a lot of noise
# if logged on every healthcheck poll — still logged, but noted here.
_INFRA_PATHS = {"/health", "/ready", "/metrics"}


@app.middleware("http")
async def request_logging_and_metrics(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_s = time.perf_counter() - start
    duration_ms = round(duration_s * 1000, 2)

    path = request.url.path
    method = request.method
    status_code = response.status_code

    # Prometheus counters — always recorded regardless of path
    HTTP_REQUESTS_TOTAL.labels(
        method=method,
        path=path,
        status_code=str(status_code),
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(
        method=method,
        path=path,
    ).observe(duration_s)

    # Structured log (skip noisy infra polls if desired — currently logs all)
    _log.info(
        "http_request",
        method=method,
        path=path,
        status=status_code,
        duration_ms=duration_ms,
    )

    return response


# ---------------------------------------------------------------------------
# Business-logic routes
# ---------------------------------------------------------------------------

app.include_router(api_router)


# ---------------------------------------------------------------------------
# Infrastructure endpoints  (no auth, no rate-limit decorator)
# ---------------------------------------------------------------------------


@app.get("/health", tags=["infra"])
def health_check() -> dict[str, str]:
    """Liveness probe — returns 200 immediately without touching DB or Redis."""
    return {"status": "ok"}


@app.get("/ready", tags=["infra"])
def readiness_check() -> JSONResponse:
    """
    Readiness probe — checks real DB connectivity and Redis connectivity.

    Returns 200 only when both dependencies are reachable.
    Returns 503 with a body that names the failed dependency otherwise.
    """
    failed: list[str] = []

    # --- Database check ---
    try:
        from sqlalchemy import text

        from app.db.session import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        failed.append("database")

    # --- Redis check ---
    try:
        import redis as redis_lib

        r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
    except Exception:
        failed.append("redis")

    if failed:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "failed": failed},
        )

    return JSONResponse(
        status_code=200,
        content={"status": "ready"},
    )


@app.get("/metrics", tags=["infra"])
def metrics_endpoint() -> Response:
    """
    Prometheus metrics endpoint.  Gated by Settings.ENABLE_METRICS (default True).
    Unauthenticated — protect at the network/ingress layer in production.
    """
    if not settings.enable_metrics:
        return JSONResponse(status_code=404, content={"detail": "Metrics disabled"})

    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
