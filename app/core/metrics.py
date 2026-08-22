"""
Prometheus metrics registry for SilentSepsis.

All counters and histograms are defined here so they can be imported
by routes, middleware, and tasks without creating duplicate collectors.
"""

from prometheus_client import REGISTRY, Counter, Histogram  # noqa: F401

# ---------------------------------------------------------------------------
# HTTP request metrics
# ---------------------------------------------------------------------------

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP request count",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# ---------------------------------------------------------------------------
# Domain-level metrics
# ---------------------------------------------------------------------------

ALERTS_CREATED_TOTAL = Counter(
    "alerts_created_total",
    "Total number of sepsis alerts created",
)

CELERY_TASK_SUCCESS_TOTAL = Counter(
    "celery_task_success_total",
    "Total Celery task successes",
    ["task_name"],
)

CELERY_TASK_FAILURE_TOTAL = Counter(
    "celery_task_failure_total",
    "Total Celery task failures",
    ["task_name"],
)
