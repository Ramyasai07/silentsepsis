from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.limiter import limiter
from app.main import app


def test_login_rate_limit_exceeded():
    # Enable limiter for this test
    limiter.enabled = True

    # Configure a low rate limit for testing
    original_limit = settings.login_rate_limit
    settings.login_rate_limit = "3/minute"

    client = TestClient(app)

    try:
        # We make 3 requests. They should return 401 Unauthorized
        # (because we send bad credentials)
        # but NOT 429.
        for _ in range(3):
            response = client.post(
                "/auth/login", data={"username": "test@test.com", "password": "pwd"}
            )
            assert response.status_code == 401
            assert response.json()["detail"] == "Invalid email or password"

        # The 4th request should exceed the limit and return 429
        response = client.post(
            "/auth/login", data={"username": "test@test.com", "password": "pwd"}
        )
        assert response.status_code == 429
        assert response.json() == {
            "detail": "Rate limit exceeded: please try again later."
        }

    finally:
        # Reset limit and disable limiter
        settings.login_rate_limit = original_limit
        limiter.enabled = False


def test_bootstrap_rate_limit_exceeded():
    limiter.enabled = True
    original_limit = settings.bootstrap_rate_limit
    settings.bootstrap_rate_limit = "2/minute"

    client = TestClient(app)

    try:
        # Make 2 requests to /auth/bootstrap. They should return 403 Forbidden
        # (bad secret)
        for _ in range(2):
            response = client.post(
                "/auth/bootstrap",
                json={
                    "email": "adm@test.com",
                    "staff_id": "ADM",
                    "full_name": "Adm",
                    "password": "StrongPass123",
                    "role_name": "Admin",
                },
                headers={"X-Bootstrap-Secret": "wrong"},
            )
            assert response.status_code == 403
            assert response.json()["detail"] == "Invalid bootstrap secret"

        # The 3rd request should return 429
        response = client.post(
            "/auth/bootstrap",
            json={
                "email": "adm@test.com",
                "staff_id": "ADM",
                "full_name": "Adm",
                "password": "StrongPass123",
                "role_name": "Admin",
            },
            headers={"X-Bootstrap-Secret": "wrong"},
        )
        assert response.status_code == 429
        assert response.json() == {
            "detail": "Rate limit exceeded: please try again later."
        }

    finally:
        settings.bootstrap_rate_limit = original_limit
        limiter.enabled = False
