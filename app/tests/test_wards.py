import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import delete

from alembic import command
from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models.patient import Patient
from app.models.patient_baseline import PatientBaseline
from app.models.user import User
from app.models.ward import Ward

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def migrate_database() -> None:
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(autouse=True)
def clean_data() -> None:
    with SessionLocal() as db:
        db.execute(delete(PatientBaseline))
        db.execute(delete(Patient))
        db.execute(delete(Ward))
        db.execute(delete(User))
        db.commit()

    yield

    with SessionLocal() as db:
        db.execute(delete(PatientBaseline))
        db.execute(delete(Patient))
        db.execute(delete(Ward))
        db.execute(delete(User))
        db.commit()


def bootstrap_secret_header() -> dict[str, str]:
    return {"X-Bootstrap-Secret": settings.bootstrap_secret}


def admin_payload() -> dict[str, str]:
    return {
        "email": "admin-wards@silentsepsis.test",
        "staff_id": "ADM-WARDS",
        "full_name": "Ward Admin",
        "password": "StrongPass123",
        "role_name": "Admin",
    }


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(email: str, password: str = "StrongPass123") -> str:
    response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def admin_token() -> str:
    response = client.post(
        "/auth/bootstrap",
        json=admin_payload(),
        headers=bootstrap_secret_header(),
    )
    assert response.status_code == 201
    return login("admin-wards@silentsepsis.test")


def create_ward(
    token: str,
    name: str = "ICU",
    capacity: int = 2,
) -> dict[str, object]:
    response = client.post(
        "/wards",
        json={"name": name, "capacity": capacity},
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


def create_patient(
    token: str,
    ward_id: str,
    bed_number: str,
) -> dict[str, object]:
    response = client.post(
        "/patients",
        json={
            "name": "Test Patient",
            "age": 54,
            "sex": "FEMALE",
            "ward_id": ward_id,
            "bed_number": bed_number,
            "admission_date": "2026-08-07T08:00:00Z",
            "admission_reason": "Sepsis observation",
        },
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


def test_admin_post_wards_succeeds() -> None:
    token = admin_token()

    response = client.post(
        "/wards",
        json={"name": "Emergency", "capacity": 4},
        headers=auth_header(token),
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Emergency"
    assert response.json()["capacity"] == 4


def test_create_ward() -> None:
    token = admin_token()
    ward = create_ward(token, "Medical ICU", 3)

    assert ward["name"] == "Medical ICU"
    assert ward["capacity"] == 3


def test_list_wards() -> None:
    token = admin_token()
    create_ward(token, "Ward A", 2)
    create_ward(token, "Ward B", 5)

    response = client.get(
        "/wards",
        headers=auth_header(token),
    )

    assert response.status_code == 200
    assert [ward["name"] for ward in response.json()] == ["Ward A", "Ward B"]


def test_get_ward() -> None:
    token = admin_token()
    ward = create_ward(token)

    response = client.get(
        f"/wards/{ward['id']}",
        headers=auth_header(token),
    )

    assert response.status_code == 200
    assert response.json()["id"] == ward["id"]


def test_ward_summary() -> None:
    token = admin_token()
    ward = create_ward(token, capacity=2)
    create_patient(token, ward["id"], "A1")

    response = client.get(
        f"/wards/{ward['id']}/summary",
        headers=auth_header(token),
    )

    assert response.status_code == 200
    assert response.json()["occupied_beds"] == 1
    assert response.json()["available_beds"] == 1
    assert response.json()["totalPatients"] == 1


def test_ward_not_found() -> None:
    token = admin_token()

    response = client.get(
        "/wards/00000000-0000-0000-0000-000000000000",
        headers=auth_header(token),
    )

    assert response.status_code == 404
