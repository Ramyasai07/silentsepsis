from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import delete

from alembic import command
from alembic.config import Config
from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def migrate_database() -> None:
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(autouse=True)
def clean_users() -> None:
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()
    yield
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()


def admin_payload(
    *,
    email: str = "admin@silentsepsis.test",
    staff_id: str = "ADM-001",
    password: str = "StrongPass123",
    role_name: str = "Admin",
) -> dict[str, str]:
    return {
        "email": email,
        "staff_id": staff_id,
        "full_name": "Hospital Admin",
        "password": password,
        "role_name": role_name,
    }


def create_payload(role_name: str, email: str, staff_id: str) -> dict[str, str]:
    return {
        "email": email,
        "staff_id": staff_id,
        "full_name": f"{role_name} User",
        "password": "StrongPass123",
        "role_name": role_name,
    }


def bootstrap_secret_header(value: str | None = None) -> dict[str, str]:
    return {"X-Bootstrap-Secret": value or settings.bootstrap_secret}


def bootstrap_admin() -> dict[str, str]:
    response = client.post(
        "/auth/bootstrap",
        json=admin_payload(),
        headers=bootstrap_secret_header(),
    )
    assert response.status_code == 201
    return login("admin@silentsepsis.test", "StrongPass123")


def login(email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_user_as_admin(
    role_name: str, email: str, staff_id: str
) -> dict[str, object]:
    token = bootstrap_admin()["access_token"]
    response = client.post(
        "/auth/users",
        json=create_payload(role_name, email, staff_id),
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


def test_bootstrap_first_admin() -> None:
    response = client.post(
        "/auth/bootstrap",
        json=admin_payload(),
        headers=bootstrap_secret_header(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "admin@silentsepsis.test"
    assert body["staff_id"] == "ADM-001"
    assert body["role"] == "Admin"
    assert "hashed_password" not in body


def test_bootstrap_rejected_after_admin_exists() -> None:
    first = client.post(
        "/auth/bootstrap",
        json=admin_payload(),
        headers=bootstrap_secret_header(),
    )
    second = client.post(
        "/auth/bootstrap",
        json=admin_payload(email="second@silentsepsis.test", staff_id="ADM-002"),
        headers=bootstrap_secret_header(),
    )

    assert first.status_code == 201
    assert second.status_code == 403


def test_bootstrap_missing_secret_rejected() -> None:
    response = client.post("/auth/bootstrap", json=admin_payload())

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid bootstrap secret"


def test_bootstrap_incorrect_secret_rejected() -> None:
    response = client.post(
        "/auth/bootstrap",
        json=admin_payload(),
        headers=bootstrap_secret_header("incorrect-secret"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid bootstrap secret"


def test_bootstrap_correct_secret_creates_first_admin() -> None:
    response = client.post(
        "/auth/bootstrap",
        json=admin_payload(),
        headers=bootstrap_secret_header(),
    )

    assert response.status_code == 201
    assert response.json()["role"] == "Admin"


def test_second_bootstrap_with_correct_secret_still_rejected() -> None:
    first = client.post(
        "/auth/bootstrap",
        json=admin_payload(),
        headers=bootstrap_secret_header(),
    )
    second = client.post(
        "/auth/bootstrap",
        json=admin_payload(email="second@silentsepsis.test", staff_id="ADM-002"),
        headers=bootstrap_secret_header(),
    )

    assert first.status_code == 201
    assert second.status_code == 403


def test_login_success() -> None:
    bootstrap_admin()

    response = client.post(
        "/auth/login",
        data={"username": "admin@silentsepsis.test", "password": "StrongPass123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password() -> None:
    bootstrap_admin()

    response = client.post(
        "/auth/login",
        data={"username": "admin@silentsepsis.test", "password": "wrongpassword"},
    )

    assert response.status_code == 401


def test_login_invalid_email() -> None:
    response = client.post(
        "/auth/login",
        data={"username": "missing@silentsepsis.test", "password": "StrongPass123"},
    )

    assert response.status_code == 401


def test_auth_me_works() -> None:
    token = bootstrap_admin()["access_token"]

    response = client.get("/auth/me", headers=auth_header(token))

    assert response.status_code == 200
    assert response.json()["role"] == "Admin"


def test_unauthorized_request_rejected() -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_invalid_jwt_rejected() -> None:
    response = client.get("/auth/me", headers=auth_header("not-a-jwt"))

    assert response.status_code == 401


def test_malformed_jwt_rejected() -> None:
    malformed_token = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000000",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )

    response = client.get("/auth/me", headers=auth_header(malformed_token))

    assert response.status_code == 401


def test_expired_jwt_rejected() -> None:
    expired_token = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000000",
            "role": "Admin",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )

    response = client.get("/auth/me", headers=auth_header(expired_token))

    assert response.status_code == 401
    assert response.json()["detail"] == "Token has expired"


def test_admin_creates_nurse() -> None:
    user = create_user_as_admin("Nurse", "nurse@silentsepsis.test", "NUR-001")

    assert user["role"] == "Nurse"
    assert user["staff_id"] == "NUR-001"


def test_admin_creates_physician() -> None:
    user = create_user_as_admin(
        "Physician",
        "physician@silentsepsis.test",
        "PHY-001",
    )

    assert user["role"] == "Physician"
    assert user["staff_id"] == "PHY-001"


def test_nurse_cannot_create_users() -> None:
    create_user_as_admin("Nurse", "nurse@silentsepsis.test", "NUR-001")
    nurse_token = login("nurse@silentsepsis.test", "StrongPass123")["access_token"]

    response = client.post(
        "/auth/users",
        json=create_payload("Nurse", "nurse2@silentsepsis.test", "NUR-002"),
        headers=auth_header(nurse_token),
    )

    assert response.status_code == 403


def test_physician_cannot_create_users() -> None:
    create_user_as_admin("Physician", "physician@silentsepsis.test", "PHY-001")
    physician_token = login("physician@silentsepsis.test", "StrongPass123")[
        "access_token"
    ]

    response = client.post(
        "/auth/users",
        json=create_payload("Nurse", "nurse@silentsepsis.test", "NUR-001"),
        headers=auth_header(physician_token),
    )

    assert response.status_code == 403


def test_duplicate_email_rejected() -> None:
    token = bootstrap_admin()["access_token"]
    first = client.post(
        "/auth/users",
        json=create_payload("Nurse", "nurse@silentsepsis.test", "NUR-001"),
        headers=auth_header(token),
    )
    duplicate = client.post(
        "/auth/users",
        json=create_payload("Physician", "nurse@silentsepsis.test", "PHY-001"),
        headers=auth_header(token),
    )

    assert first.status_code == 201
    assert duplicate.status_code == 400


def test_duplicate_staff_id_rejected() -> None:
    token = bootstrap_admin()["access_token"]
    first = client.post(
        "/auth/users",
        json=create_payload("Nurse", "nurse@silentsepsis.test", "NUR-001"),
        headers=auth_header(token),
    )
    duplicate = client.post(
        "/auth/users",
        json=create_payload("Physician", "physician@silentsepsis.test", "NUR-001"),
        headers=auth_header(token),
    )

    assert first.status_code == 201
    assert duplicate.status_code == 400


def test_invalid_role_rejected() -> None:
    token = bootstrap_admin()["access_token"]

    response = client.post(
        "/auth/users",
        json=create_payload("Pharmacist", "pharm@silentsepsis.test", "PHA-001"),
        headers=auth_header(token),
    )

    assert response.status_code == 400
