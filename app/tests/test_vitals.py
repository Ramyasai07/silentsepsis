from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

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
from app.models.vital_reading import VitalReading
from app.models.ward import Ward

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def migrate_database() -> None:
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(autouse=True)
def clean_data() -> None:
    with SessionLocal() as db:
        db.execute(delete(VitalReading))
        db.execute(delete(PatientBaseline))
        db.execute(delete(Patient))
        db.execute(delete(Ward))
        db.execute(delete(User))
        db.commit()
    yield
    with SessionLocal() as db:
        db.execute(delete(VitalReading))
        db.execute(delete(PatientBaseline))
        db.execute(delete(Patient))
        db.execute(delete(Ward))
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


def login(email: str, password: str = "StrongPass123") -> dict[str, str]:
    response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def bootstrap_admin() -> str:
    response = client.post(
        "/auth/bootstrap",
        json=admin_payload(),
        headers=bootstrap_secret_header(),
    )
    assert response.status_code == 201
    return login("admin@silentsepsis.test", "StrongPass123")["access_token"]


def create_user_as_admin(
    role_name: str, email: str, staff_id: str, admin_token: str
) -> dict[str, object]:
    response = client.post(
        "/auth/users",
        json=create_payload(role_name, email, staff_id),
        headers=auth_header(admin_token),
    )
    assert response.status_code == 201
    return response.json()


def create_ward(token: str, name: str = "ICU", capacity: int = 2) -> dict[str, object]:
    response = client.post(
        "/wards",
        json={"name": name, "capacity": capacity},
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


def create_patient(
    token: str, ward_id: UUID, name: str = "Test Patient", bed_number: str = "A1"
) -> dict[str, object]:
    response = client.post(
        "/patients",
        json={
            "name": name,
            "age": 50,
            "sex": "FEMALE",
            "ward_id": str(ward_id),
            "bed_number": bed_number,
            "admission_date": "2026-08-07T08:00:00Z",
            "admission_reason": "Sepsis observation",
        },
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


def vital_payload(recorded_at: datetime | None = None) -> dict[str, object]:
    payload = {
        "heart_rate": 80,
        "respiratory_rate": 18,
        "systolic_bp": 120,
        "diastolic_bp": 75,
        "spo2": 98.0,
        "temperature": 36.8,
    }
    if recorded_at is not None:
        payload["recorded_at"] = recorded_at.isoformat()
    return payload


def test_single_vital_submission_happy_path() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))
    response = client.post(
        f"/patients/{patient['id']}/vitals",
        json=vital_payload(),
        headers=auth_header(admin_token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["patient_id"] == patient["id"]
    assert body["heart_rate"] == 80
    assert body["respiratory_rate"] == 18
    assert body["systolic_bp"] == 120
    assert body["diastolic_bp"] == 75
    assert body["spo2"] == 98.0
    assert body["temperature"] == 36.8
    assert body["recorded_by"] is not None


def test_batch_vitals_submission_happy_path() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))

    readings = [
        {**vital_payload(datetime.now(timezone.utc) - timedelta(minutes=3))},
        {**vital_payload(datetime.now(timezone.utc) - timedelta(minutes=2))},
        {**vital_payload(datetime.now(timezone.utc) - timedelta(minutes=1))},
    ]
    response = client.post(
        f"/patients/{patient['id']}/vitals/batch",
        json={"patient_id": patient["id"], "readings": readings},
        headers=auth_header(admin_token),
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body) == 3
    assert all(item["patient_id"] == patient["id"] for item in body)


def test_batch_atomicity_rejects_all_on_invalid_reading() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))

    readings = [
        {**vital_payload(datetime.now(timezone.utc) - timedelta(minutes=3))},
        {
            **vital_payload(datetime.now(timezone.utc) - timedelta(minutes=2)),
            "heart_rate": 500,
        },
    ]
    response = client.post(
        f"/patients/{patient['id']}/vitals/batch",
        json={"patient_id": patient["id"], "readings": readings},
        headers=auth_header(admin_token),
    )

    assert response.status_code == 422

    history = client.get(
        f"/patients/{patient['id']}/vitals", headers=auth_header(admin_token)
    )
    assert history.status_code == 200
    assert history.json() == []


def test_out_of_range_heart_rate_rejected() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))

    response = client.post(
        f"/patients/{patient['id']}/vitals",
        json={**vital_payload(), "heart_rate": 500},
        headers=auth_header(admin_token),
    )

    assert response.status_code == 422


def test_invalid_blood_pressure_relationship_rejected() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))

    response = client.post(
        f"/patients/{patient['id']}/vitals",
        json={**vital_payload(), "systolic_bp": 120, "diastolic_bp": 120},
        headers=auth_header(admin_token),
    )

    assert response.status_code == 422


def test_future_dated_reading_rejected() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))

    future_timestamp = datetime.now(timezone.utc) + timedelta(minutes=6)
    response = client.post(
        f"/patients/{patient['id']}/vitals",
        json={**vital_payload(future_timestamp)},
        headers=auth_header(admin_token),
    )

    assert response.status_code == 422


def test_empty_batch_rejected() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))

    response = client.post(
        f"/patients/{patient['id']}/vitals/batch",
        json={"patient_id": patient["id"], "readings": []},
        headers=auth_header(admin_token),
    )

    assert response.status_code == 422

    history = client.get(
        f"/patients/{patient['id']}/vitals", headers=auth_header(admin_token)
    )
    assert history.status_code == 200
    assert history.json() == []


def test_oversized_batch_rejected() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))

    readings = [
        vital_payload(datetime.now(timezone.utc) - timedelta(minutes=i))
        for i in range(101)
    ]
    response = client.post(
        f"/patients/{patient['id']}/vitals/batch",
        json={"patient_id": patient["id"], "readings": readings},
        headers=auth_header(admin_token),
    )

    assert response.status_code == 422

    history = client.get(
        f"/patients/{patient['id']}/vitals", headers=auth_header(admin_token)
    )
    assert history.status_code == 200
    assert history.json() == []


def test_conflicting_batch_patient_id_rejected() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))
    other_patient_id = str(uuid4())

    response = client.post(
        f"/patients/{patient['id']}/vitals/batch",
        json={
            "patient_id": other_patient_id,
            "readings": [
                vital_payload(datetime.now(timezone.utc) - timedelta(minutes=3))
            ],
        },
        headers=auth_header(admin_token),
    )

    assert response.status_code == 422

    history = client.get(
        f"/patients/{patient['id']}/vitals", headers=auth_header(admin_token)
    )
    assert history.status_code == 200
    assert history.json() == []


def test_history_ordering_newest_first() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))

    readings = [
        vital_payload(datetime.now(timezone.utc) - timedelta(minutes=3)),
        vital_payload(datetime.now(timezone.utc) - timedelta(minutes=1)),
        vital_payload(datetime.now(timezone.utc) - timedelta(minutes=2)),
    ]
    response = client.post(
        f"/patients/{patient['id']}/vitals/batch",
        json={"patient_id": patient["id"], "readings": readings},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 201

    history = client.get(
        f"/patients/{patient['id']}/vitals", headers=auth_header(admin_token)
    )
    assert history.status_code == 200
    returned = history.json()
    assert len(returned) == 3
    assert returned[0]["recorded_at"] > returned[1]["recorded_at"]
    assert returned[1]["recorded_at"] > returned[2]["recorded_at"]


def test_time_range_filtering() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))

    first = datetime.now(timezone.utc) - timedelta(minutes=10)
    second = datetime.now(timezone.utc) - timedelta(minutes=5)
    third = datetime.now(timezone.utc) - timedelta(minutes=1)

    response = client.post(
        f"/patients/{patient['id']}/vitals/batch",
        json={
            "patient_id": patient["id"],
            "readings": [
                vital_payload(first),
                vital_payload(second),
                vital_payload(third),
            ],
        },
        headers=auth_header(admin_token),
    )
    assert response.status_code == 201

    history = client.get(
        f"/patients/{patient['id']}/vitals",
        params={"start_time": second.isoformat(), "end_time": third.isoformat()},
        headers=auth_header(admin_token),
    )
    assert history.status_code == 200
    items = history.json()
    assert len(items) == 2
    assert all(item["recorded_at"] >= second.isoformat() for item in items)


def test_nurse_can_submit_vitals() -> None:
    admin_token = bootstrap_admin()
    nurse = create_user_as_admin(
        "Nurse", "nurse@silentsepsis.test", "NUR-001", admin_token
    )
    nurse_token = login("nurse@silentsepsis.test", "StrongPass123")["access_token"]
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))

    response = client.post(
        f"/patients/{patient['id']}/vitals",
        json=vital_payload(),
        headers=auth_header(nurse_token),
    )
    assert response.status_code == 201
    assert response.json()["recorded_by"] == nurse["id"]


def test_unauthenticated_requests_are_rejected() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))

    response = client.post(
        f"/patients/{patient['id']}/vitals",
        json=vital_payload(),
    )
    assert response.status_code == 401

    history = client.get(f"/patients/{patient['id']}/vitals")
    assert history.status_code == 401


def test_invalid_patient_returns_404() -> None:
    admin_token = bootstrap_admin()
    bad_patient_id = uuid4()

    response = client.post(
        f"/patients/{bad_patient_id}/vitals",
        json=vital_payload(),
        headers=auth_header(admin_token),
    )
    assert response.status_code == 404


def test_latest_endpoint_returns_newest_reading() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))

    response = client.post(
        f"/patients/{patient['id']}/vitals/batch",
        json={
            "patient_id": patient["id"],
            "readings": [
                vital_payload(datetime.now(timezone.utc) - timedelta(minutes=4)),
                vital_payload(datetime.now(timezone.utc) - timedelta(minutes=1)),
            ],
        },
        headers=auth_header(admin_token),
    )
    assert response.status_code == 201

    latest = client.get(
        f"/patients/{patient['id']}/vitals/latest", headers=auth_header(admin_token)
    )
    assert latest.status_code == 200
    assert latest.json()["recorded_at"] == max(
        item["recorded_at"] for item in response.json()
    )


def test_query_pagination_returns_correct_subset() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))

    response = client.post(
        f"/patients/{patient['id']}/vitals/batch",
        json={
            "patient_id": patient["id"],
            "readings": [
                vital_payload(datetime.now(timezone.utc) - timedelta(minutes=4)),
                vital_payload(datetime.now(timezone.utc) - timedelta(minutes=3)),
                vital_payload(datetime.now(timezone.utc) - timedelta(minutes=2)),
            ],
        },
        headers=auth_header(admin_token),
    )
    assert response.status_code == 201

    history = client.get(
        f"/patients/{patient['id']}/vitals?limit=2&offset=1",
        headers=auth_header(admin_token),
    )
    assert history.status_code == 200
    assert len(history.json()) == 2
