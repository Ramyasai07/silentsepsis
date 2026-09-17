import pytest

from app.tests.conftest import validate_test_database_url


def test_test_database_guard_rejects_application_database() -> None:
    with pytest.raises(RuntimeError, match="silentsepsis.*not a test database"):
        validate_test_database_url(
            "postgresql://postgres:postgres@db:5432/silentsepsis"
        )


def test_test_database_guard_accepts_test_database() -> None:
    validate_test_database_url(
        "postgresql://postgres:postgres@db:5432/silentsepsis_test"
    )
