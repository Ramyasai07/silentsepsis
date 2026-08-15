from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.limiter import limiter

tags_metadata = [
    {
        "name": "auth",
        "description": "Authentication and user management operations including admin bootstrapping.",
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
        "description": "Sepsis risk evaluations, prediction history, and explanation features.",
    },
    {
        "name": "alerts",
        "description": "Real-time sepsis alerts, acknowledgements, resolutions, and lifecycle management.",
    },
    {
        "name": "feedback",
        "description": "Clinician feedback submission and annotations on model alerts.",
    },
    {
        "name": "audit-logs",
        "description": "Auditing and tracking of critical clinician actions and system changes.",
    },
    {
        "name": "analytics",
        "description": "Sepsis incidence analytics, ward statistics, and model performance metrics.",
    },
    {
        "name": "tasks/admin",
        "description": "Administrative tasks, celery worker diagnostics, and maintenance routines.",
    },
]

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
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded: please try again later."},
    )


# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


app.include_router(api_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
