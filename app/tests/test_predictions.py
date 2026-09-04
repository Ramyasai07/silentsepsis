from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from alembic import command
from alembic.config import Config
from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.ml.base import FeatureContribution, PredictionResult, RiskPredictor
from app.models.patient import Patient
from app.models.patient_baseline import PatientBaseline
from app.models.prediction import Prediction
from app.models.prediction_feature import PredictionFeature
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
        db.execute(delete(PredictionFeature))
        db.execute(delete(Prediction))
        db.execute(delete(VitalReading))
        db.execute(delete(PatientBaseline))
        db.execute(delete(Patient))
        db.execute(delete(Ward))
        db.execute(delete(User))
        db.commit()
    yield
    with SessionLocal() as db:
        db.execute(delete(PredictionFeature))
        db.execute(delete(Prediction))
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


def set_patient_baseline(
    token: str, patient_id: UUID, baseline: dict[str, object]
) -> dict[str, object]:
    response = client.post(
        f"/patients/{patient_id}/baseline",
        json=baseline,
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


def create_prediction(
    token: str, patient_id: UUID, vital_reading_id: UUID | None = None
) -> dict[str, object]:
    payload = {"patient_id": str(patient_id)}
    if vital_reading_id is not None:
        payload["vital_reading_id"] = str(vital_reading_id)
    response = client.post(
        f"/patients/{patient_id}/predictions",
        json=payload,
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


def create_vital(
    token: str, patient_id: UUID, recorded_at: datetime | None = None
) -> dict[str, object]:
    response = client.post(
        f"/patients/{patient_id}/vitals",
        json=vital_payload(recorded_at),
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


def create_vital_batch(
    token: str, patient_id: UUID, readings: list[dict[str, object]]
) -> list[dict[str, object]]:
    response = client.post(
        f"/patients/{patient_id}/vitals/batch",
        json={"patient_id": str(patient_id), "readings": readings},
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


def get_prediction_history(
    token: str, patient_id: UUID, params: dict[str, object] | None = None
) -> list[dict[str, object]]:
    response = client.get(
        f"/patients/{patient_id}/predictions",
        headers=auth_header(token),
        params=params,
    )
    assert response.status_code == 200
    return response.json()


def get_latest_prediction(token: str, patient_id: UUID) -> dict[str, object]:
    response = client.get(
        f"/patients/{patient_id}/predictions/latest",
        headers=auth_header(token),
    )
    assert response.status_code == 200
    return response.json()


def test_generate_prediction_happy_path() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))
    vital = create_vital(admin_token, UUID(patient["id"]))

    prediction = create_prediction(admin_token, UUID(patient["id"]), UUID(vital["id"]))

    assert 0.0 <= prediction["risk_score"] <= 1.0
    assert prediction["risk_tier"] in {"LOW", "MODERATE", "HIGH", "CRITICAL"}
    assert len(prediction["features"]) == 15
    assert prediction["patient_id"] == patient["id"]
    assert prediction["vital_reading_id"] == vital["id"]


def test_feature_contributions_are_sorted_by_absolute_value() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))
    vital = create_vital(
        admin_token,
        UUID(patient["id"]),
        datetime.now(timezone.utc) - timedelta(minutes=2),
    )

    prediction = create_prediction(admin_token, UUID(patient["id"]), UUID(vital["id"]))
    values = [abs(item["contribution"]) for item in prediction["features"]]

    assert values == sorted(values, reverse=True)


def test_prediction_uses_patient_baseline() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))
    vital = create_vital(
        admin_token,
        UUID(patient["id"]),
        datetime.now(timezone.utc) - timedelta(minutes=4),
    )

    first_prediction = create_prediction(
        admin_token, UUID(patient["id"]), UUID(vital["id"])
    )
    baseline = {
        "baseline_hr": 70.0,
        "baseline_spo2": 99.0,
        "baseline_temperature": 36.8,
        "baseline_rr": 16.0,
        "baseline_systolic_bp": 110.0,
        "baseline_diastolic_bp": 70.0,
        "calculated_from_hours": 24,
    }
    set_patient_baseline(admin_token, UUID(patient["id"]), baseline)
    second_prediction = create_prediction(
        admin_token, UUID(patient["id"]), UUID(vital["id"])
    )

    assert first_prediction["risk_score"] != second_prediction["risk_score"]
    assert first_prediction["features"] != second_prediction["features"]


def test_partial_baseline_falls_back_to_population_normals() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))
    vital = create_vital(
        admin_token,
        UUID(patient["id"]),
        datetime.now(timezone.utc) - timedelta(minutes=3),
    )

    no_baseline = create_prediction(admin_token, UUID(patient["id"]), UUID(vital["id"]))
    baseline = {
        "baseline_hr": 75.0,
        "baseline_spo2": None,
        "baseline_temperature": 36.8,
        "baseline_rr": None,
        "baseline_systolic_bp": None,
        "baseline_diastolic_bp": None,
        "calculated_from_hours": 24,
    }
    set_patient_baseline(admin_token, UUID(patient["id"]), baseline)
    partial_baseline = create_prediction(
        admin_token, UUID(patient["id"]), UUID(vital["id"])
    )

    no_baseline_map = {item["feature_name"]: item for item in no_baseline["features"]}
    partial_baseline_map = {
        item["feature_name"]: item for item in partial_baseline["features"]
    }

    assert (
        no_baseline_map["O2Sat"]["contribution"]
        == partial_baseline_map["O2Sat"]["contribution"]
    )
    assert (
        no_baseline_map["Resp"]["contribution"]
        == partial_baseline_map["Resp"]["contribution"]
    )
    assert (
        no_baseline_map["SBP"]["contribution"]
        == partial_baseline_map["SBP"]["contribution"]
    )
    assert (
        no_baseline_map["DBP"]["contribution"]
        == partial_baseline_map["DBP"]["contribution"]
    )
    assert (
        no_baseline_map["HR"]["contribution"]
        != partial_baseline_map["HR"]["contribution"]
    )
    assert (
        no_baseline_map["Temp"]["contribution"]
        != partial_baseline_map["Temp"]["contribution"]
    )


def test_no_baseline_fallback_uses_population_normals() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))
    vital = create_vital(
        admin_token,
        UUID(patient["id"]),
        datetime.now(timezone.utc) - timedelta(minutes=4),
    )

    prediction = create_prediction(admin_token, UUID(patient["id"]), UUID(vital["id"]))
    assert prediction["risk_score"] >= 0.0
    assert prediction["risk_tier"] in {"LOW", "MODERATE", "HIGH", "CRITICAL"}


def test_prediction_is_deterministic_for_identical_input() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))
    vital = create_vital(
        admin_token,
        UUID(patient["id"]),
        datetime.now(timezone.utc) - timedelta(minutes=5),
    )

    first_prediction = create_prediction(
        admin_token, UUID(patient["id"]), UUID(vital["id"])
    )
    second_prediction = create_prediction(
        admin_token, UUID(patient["id"]), UUID(vital["id"])
    )

    assert first_prediction["risk_score"] == second_prediction["risk_score"]
    assert first_prediction["risk_tier"] == second_prediction["risk_tier"]
    assert first_prediction["features"] == second_prediction["features"]


def test_prediction_persistence_creates_prediction_and_features() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))
    vital = create_vital(
        admin_token,
        UUID(patient["id"]),
        datetime.now(timezone.utc) - timedelta(minutes=4),
    )

    create_prediction(admin_token, UUID(patient["id"]), UUID(vital["id"]))

    with SessionLocal() as db:
        prediction_count = db.scalar(select(func.count()).select_from(Prediction))
        feature_count = db.scalar(select(func.count()).select_from(PredictionFeature))

    assert prediction_count == 1
    assert feature_count == 15


def test_prediction_persistence_atomicity_rolls_back_on_feature_error() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))
    vital = create_vital(
        admin_token,
        UUID(patient["id"]),
        datetime.now(timezone.utc) - timedelta(minutes=3),
    )

    class BrokenPredictor(RiskPredictor):
        def predict(
            self, vitals: VitalReading, baseline: PatientBaseline | None
        ) -> PredictionResult:
            return PredictionResult(
                risk_score=0.5,
                risk_tier="MODERATE",
                feature_contributions=[
                    FeatureContribution(
                        feature_name="x" * 200, contribution=0.5, feature_value=1.0
                    ),
                ],
            )

    from app.services.prediction_service import PredictionService

    service = PredictionService(BrokenPredictor())

    with SessionLocal() as db:
        with pytest.raises(Exception):
            service.generate_prediction(db, UUID(patient["id"]), UUID(vital["id"]))

    with SessionLocal() as db:
        prediction_count = db.scalar(select(func.count()).select_from(Prediction))
        feature_count = db.scalar(select(func.count()).select_from(PredictionFeature))

    assert prediction_count == 0
    assert feature_count == 0


def test_post_prediction_with_missing_vitals_returns_409() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))

    response = client.post(
        f"/patients/{patient['id']}/predictions",
        json={"patient_id": patient["id"]},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 409


def test_prediction_for_nonexistent_patient_returns_404() -> None:
    admin_token = bootstrap_admin()
    bad_patient_id = str(uuid4())

    response = client.post(
        f"/patients/{bad_patient_id}/predictions",
        json={"patient_id": bad_patient_id},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 404


def test_mismatched_vital_reading_id_returns_404() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient_a = create_patient(
        admin_token, UUID(ward["id"]), name="Patient A", bed_number="A1"
    )
    patient_b = create_patient(
        admin_token, UUID(ward["id"]), name="Patient B", bed_number="A2"
    )
    vital_b = create_vital(
        admin_token,
        UUID(patient_b["id"]),
        datetime.now(timezone.utc) - timedelta(minutes=2),
    )

    response = client.post(
        f"/patients/{patient_a['id']}/predictions",
        json={"patient_id": patient_a["id"], "vital_reading_id": vital_b["id"]},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 404


def test_prediction_history_orders_newest_first() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))
    first = create_vital(
        admin_token,
        UUID(patient["id"]),
        datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    second = create_vital(
        admin_token,
        UUID(patient["id"]),
        datetime.now(timezone.utc) - timedelta(minutes=4),
    )

    create_prediction(admin_token, UUID(patient["id"]), UUID(first["id"]))
    create_prediction(admin_token, UUID(patient["id"]), UUID(second["id"]))

    history = client.get(
        f"/patients/{patient['id']}/predictions",
        headers=auth_header(admin_token),
    )
    assert history.status_code == 200
    assert len(history.json()) == 2
    assert history.json()[0]["created_at"] >= history.json()[1]["created_at"]


def test_latest_prediction_endpoint_returns_newest_prediction() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))
    first = create_vital(
        admin_token,
        UUID(patient["id"]),
        datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    second = create_vital(
        admin_token,
        UUID(patient["id"]),
        datetime.now(timezone.utc) - timedelta(minutes=2),
    )

    create_prediction(admin_token, UUID(patient["id"]), UUID(first["id"]))
    newest = create_prediction(admin_token, UUID(patient["id"]), UUID(second["id"]))

    response = client.get(
        f"/patients/{patient['id']}/predictions/latest",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["id"] == newest["id"]


def test_roles_allowed_to_trigger_prediction() -> None:
    admin_token = bootstrap_admin()
    create_user_as_admin("Nurse", "nurse@silentsepsis.test", "NUR-001", admin_token)
    create_user_as_admin(
        "Physician", "physician@silentsepsis.test", "PHY-001", admin_token
    )
    nurse_token = login("nurse@silentsepsis.test")["access_token"]
    physician_token = login("physician@silentsepsis.test")["access_token"]

    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))
    vital = create_vital(
        admin_token,
        UUID(patient["id"]),
        datetime.now(timezone.utc) - timedelta(minutes=3),
    )

    for token in [admin_token, nurse_token, physician_token]:
        response = client.post(
            f"/patients/{patient['id']}/predictions",
            json={"patient_id": patient["id"], "vital_reading_id": vital["id"]},
            headers=auth_header(token),
        )
        assert response.status_code == 201


def test_unauthenticated_requests_are_rejected() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))

    response = client.post(
        f"/patients/{patient['id']}/predictions",
        json={"patient_id": patient["id"]},
    )
    assert response.status_code == 401


def test_history_pagination_behaves_as_expected() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))
    readings = [
        create_vital(
            admin_token,
            UUID(patient["id"]),
            datetime.now(timezone.utc) - timedelta(minutes=5),
        ),
        create_vital(
            admin_token,
            UUID(patient["id"]),
            datetime.now(timezone.utc) - timedelta(minutes=4),
        ),
        create_vital(
            admin_token,
            UUID(patient["id"]),
            datetime.now(timezone.utc) - timedelta(minutes=3),
        ),
    ]

    for reading in readings:
        create_prediction(admin_token, UUID(patient["id"]), UUID(reading["id"]))

    response = client.get(
        f"/patients/{patient['id']}/predictions",
        headers=auth_header(admin_token),
        params={"limit": 1, "offset": 1},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_nonexistent_patient_history_and_latest_return_expected_results() -> None:
    admin_token = bootstrap_admin()
    bad_patient_id = str(uuid4())

    history_response = client.get(
        f"/patients/{bad_patient_id}/predictions",
        headers=auth_header(admin_token),
    )
    latest_response = client.get(
        f"/patients/{bad_patient_id}/predictions/latest",
        headers=auth_header(admin_token),
    )

    assert history_response.status_code == 404
    assert latest_response.status_code == 404


def test_empty_prediction_history_returns_empty_list_and_latest_returns_404() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))

    history_response = client.get(
        f"/patients/{patient['id']}/predictions",
        headers=auth_header(admin_token),
    )
    latest_response = client.get(
        f"/patients/{patient['id']}/predictions/latest",
        headers=auth_header(admin_token),
    )

    assert history_response.status_code == 200
    assert history_response.json() == []
    assert latest_response.status_code == 404
