import pytest
from app.core.limiter import limiter

@pytest.fixture(scope="session", autouse=True)
def disable_limiter() -> None:
    limiter.enabled = False
