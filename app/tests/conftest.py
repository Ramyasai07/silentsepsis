from urllib.parse import urlparse

import pytest

from app.core.config import settings
from app.core.limiter import limiter


def validate_test_database_url(database_url: str) -> None:
    database_name = urlparse(database_url).path.lstrip("/")
    if not database_name.endswith("_test"):
        raise RuntimeError(
            "Refusing to run tests: TEST_DATABASE_URL resolves to database "
            f"'{database_name or '<missing>'}', which is not a test database. "
            "The database name must end with '_test'."
        )


validate_test_database_url(settings.test_database_url)
settings.database_url = settings.test_database_url


@pytest.fixture(scope="session", autouse=True)
def configure_test_database() -> None:
    """Keep all imported application sessions bound to the isolated database."""

    validate_test_database_url(settings.test_database_url)


@pytest.fixture(scope="session", autouse=True)
def disable_limiter() -> None:
    limiter.enabled = False
