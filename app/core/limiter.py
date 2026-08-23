from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.default_rate_limit]
)

def get_login_rate_limit() -> str:
    return settings.login_rate_limit

def get_bootstrap_rate_limit() -> str:
    return settings.bootstrap_rate_limit
