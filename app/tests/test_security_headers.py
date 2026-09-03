from fastapi.testclient import TestClient

from app.main import app


def test_security_headers_present():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    # HSTS should be absent on HTTP
    assert "Strict-Transport-Security" not in response.headers


def test_hsts_on_https():
    client = TestClient(app, base_url="https://testserver")
    response = client.get("/health")
    assert response.status_code == 200
    assert "Strict-Transport-Security" in response.headers
    assert (
        response.headers["Strict-Transport-Security"]
        == "max-age=31536000; includeSubDomains"
    )


def test_cors_allowed_origin():
    client = TestClient(app)
    # http://localhost:5173 is the default allowed origin in Settings/example env
    headers = {"Origin": "http://localhost:5173"}
    response = client.get("/health", headers=headers)
    assert (
        response.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
    )


def test_cors_disallowed_origin():
    client = TestClient(app)
    headers = {"Origin": "http://malicious-origin.com"}
    response = client.get("/health", headers=headers)
    assert response.headers.get("Access-Control-Allow-Origin") is None
