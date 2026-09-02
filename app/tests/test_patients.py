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


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def admin_payload() -> dict[str, str]:
    return {
        "email": "admin-patients@silentsepsis.test",
        "staff_id": "ADM-PATIENTS",
        "full_name": "Patient Admin",
        "password": "StrongPass123",
        "role_name": "Admin",
    }


def create_user_payload(role_name: str, email: str, staff_id: str) -> dict[str, str]:
    return {
        "email": email,
        "staff_id": staff_id,
        "full_name": f"{role_name} User",
        "password": "StrongPass123",
        "role_name": role_name,
    }


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
    assert response.status_code in (201, 403)
    return login("admin-patients@silentsepsis.test")


def staff_token(role_name: str, admin_token_value: str | None = None) -> str:
    token = admin_token_value or admin_token()
    email = f"{role_name.lower()}@silentsepsis.test"
    response = client.post(
        "/auth/users",
        json=create_user_payload(role_name, email, f"{role_name.upper()}-001"),
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return login(email)


def create_ward(token: str, name: str = "ICU", capacity: int = 2) -> dict[str, object]:
    response = client.post(
        "/wards",
        json={"name": name, "capacity": capacity},
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


def patient_payload(
    ward_id: str,
    *,
    name: str = "Test Patient",
    bed_number: str = "A1",
) -> dict[str, object]:
    return {
        "name": name,
        "age": 54,
        "sex": "FEMALE",
        "ward_id": ward_id,
        "bed_number": bed_number,
        "admission_date": "2026-08-07T08:00:00Z",
        "admission_reason": "Sepsis observation",
    }


def create_patient(
    token: str,
    ward_id: str,
    *,
    name: str = "Test Patient",
    bed_number: str = "A1",
) -> dict[str, object]:
    response = client.post(
        "/patients",
        json=patient_payload(ward_id, name=name, bed_number=bed_number),
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


def test_create_patient() -> None:
    token = admin_token()
    ward = create_ward(token)

    patient = create_patient(token, ward["id"])

    assert patient["name"] == "Test Patient"
    assert patient["ward"]["id"] == ward["id"]
    assert patient["bed_number"] == "A1"


def test_physician_post_patients_succeeds() -> None:
    admin = admin_token()
    physician_token = staff_token("Physician", admin)
    ward = create_ward(admin, "Physician Ward", 2)

    response = client.post(
        "/patients",
        json=patient_payload(ward["id"]),
        headers=auth_header(physician_token),
    )

    assert response.status_code == 201


def test_nurse_post_patients_returns_403() -> None:
    admin = admin_token()
    nurse_token = staff_token("Nurse", admin)
    ward = create_ward(admin, "Nurse Ward", 2)

    response = client.post(
        "/patients",
        json=patient_payload(ward["id"]),
        headers=auth_header(nurse_token),
    )

    assert response.status_code == 403


def test_get_patient() -> None:
    token = admin_token()
    ward = create_ward(token)
    patient = create_patient(token, ward["id"])

    response = client.get(f"/patients/{patient['id']}", headers=auth_header(token))

    assert response.status_code == 200
    assert response.json()["id"] == patient["id"]


def test_update_patient() -> None:
    token = admin_token()
    ward = create_ward(token)
    patient = create_patient(token, ward["id"])

    response = client.patch(
        f"/patients/{patient['id']}",
        json={"bed_number": "A2"},
        headers=auth_header(token),
    )

    assert response.status_code == 200
    assert response.json()["bed_number"] == "A2"


def test_transfer_patient() -> None:
    token = admin_token()
    first_ward = create_ward(token, "Ward One", 2)
    second_ward = create_ward(token, "Ward Two", 2)
    patient = create_patient(token, first_ward["id"])

    response = client.patch(
        f"/patients/{patient['id']}",
        json={"ward_id": second_ward["id"], "bed_number": "B1"},
        headers=auth_header(token),
    )

    assert response.status_code == 200
    assert response.json()["ward"]["id"] == second_ward["id"]
    assert response.json()["bed_number"] == "B1"


def test_create_baseline() -> None:
    token = admin_token()
    ward = create_ward(token)
    patient = create_patient(token, ward["id"])

    response = client.post(
        f"/patients/{patient['id']}/baseline",
        json={"baseline_hr": 82, "baseline_spo2": 97, "calculated_from_hours": 12},
        headers=auth_header(token),
    )

    assert response.status_code == 201
    assert response.json()["baseline_hr"] == 82


def test_retrieve_baseline() -> None:
    token = admin_token()
    ward = create_ward(token)
    patient = create_patient(token, ward["id"])
    client.post(
        f"/patients/{patient['id']}/baseline",
        json={"baseline_hr": 82, "baseline_spo2": 97, "calculated_from_hours": 12},
        headers=auth_header(token),
    )

    response = client.get(
        f"/patients/{patient['id']}/baseline",
        headers=auth_header(token),
    )

    assert response.status_code == 200
    assert response.json()["patient_id"] == patient["id"]


def test_list_patients() -> None:
    token = admin_token()
    ward = create_ward(token)
    create_patient(token, ward["id"], name="Alpha Patient", bed_number="A1")
    create_patient(token, ward["id"], name="Beta Patient", bed_number="A2")

    response = client.get("/patients", headers=auth_header(token))

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_filter_patients_by_ward() -> None:
    token = admin_token()
    first_ward = create_ward(token, "Ward One", 2)
    second_ward = create_ward(token, "Ward Two", 2)
    create_patient(token, first_ward["id"], name="Alpha Patient", bed_number="A1")
    create_patient(token, second_ward["id"], name="Beta Patient", bed_number="B1")

    response = client.get(
        f"/patients?ward_id={first_ward['id']}",
        headers=auth_header(token),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["ward_name"] == "Ward One"


def test_patient_pagination() -> None:
    token = admin_token()
    ward = create_ward(token, capacity=3)
    create_patient(token, ward["id"], name="Alpha Patient", bed_number="A1")
    create_patient(token, ward["id"], name="Beta Patient", bed_number="A2")
    create_patient(token, ward["id"], name="Gamma Patient", bed_number="A3")

    response = client.get("/patients?limit=1&offset=1", headers=auth_header(token))

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_patient_not_found() -> None:
    token = admin_token()

    response = client.get(
        "/patients/00000000-0000-0000-0000-000000000000",
        headers=auth_header(token),
    )

    assert response.status_code == 404


def test_ward_not_found() -> None:
    token = admin_token()

    response = client.post(
        "/patients",
        json=patient_payload("00000000-0000-0000-0000-000000000000"),
        headers=auth_header(token),
    )

    assert response.status_code == 404


def test_duplicate_bed_rejection() -> None:
    token = admin_token()
    ward = create_ward(token, capacity=2)
    create_patient(token, ward["id"], bed_number="A1")

    response = client.post(
        "/patients",
        json=patient_payload(ward["id"], name="Second Patient", bed_number="A1"),
        headers=auth_header(token),
    )

    assert response.status_code == 409


def test_ward_capacity_rejection() -> None:
    token = admin_token()
    ward = create_ward(token, capacity=1)
    create_patient(token, ward["id"], bed_number="A1")

    response = client.post(
        "/patients",
        json=patient_payload(ward["id"], name="Second Patient", bed_number="A2"),
        headers=auth_header(token),
    )

    assert response.status_code == 409
