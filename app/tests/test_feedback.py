from datetime import datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from alembic import command
from alembic.config import Config
from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.ml.base import FeatureContribution, PredictionResult, RiskPredictor
from app.models.alert import Alert
from app.models.audit_log import AuditLog
from app.models.feedback import Feedback
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
        db.execute(delete(Feedback))
        db.execute(delete(AuditLog))
        db.execute(delete(Alert))
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
        db.execute(delete(Feedback))
        db.execute(delete(AuditLog))
        db.execute(delete(Alert))
        db.execute(delete(PredictionFeature))
        db.execute(delete(Prediction))
        db.execute(delete(VitalReading))
        db.execute(delete(PatientBaseline))
        db.execute(delete(Patient))
        db.execute(delete(Ward))
        db.execute(delete(User))
        db.commit()


def bootstrap_secret_header(value: str | None = None) -> dict[str, str]:
    return {"X-Bootstrap-Secret": value or settings.bootstrap_secret}


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def admin_payload(
    *,
    email: str = "admin@silentsepsis.test",
    staff_id: str = "ADM-001",
    role_name: str = "Admin",
) -> dict[str, str]:
    return {
        "email": email,
        "staff_id": staff_id,
        "full_name": f"{role_name} User",
        "password": "StrongPass123",
        "role_name": role_name,
    }


def login(email: str, password: str = "StrongPass123") -> dict[str, str]:
    response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def bootstrap_admin() -> str:
    response = client.post(
        "/auth/bootstrap",
        json=admin_payload(),
        headers=bootstrap_secret_header(),
    )
    if response.status_code == 201:
        return login("admin@silentsepsis.test")["access_token"]
    assert response.status_code == 403
    return login("admin@silentsepsis.test")["access_token"]


def create_user(admin_token: str, role_name: str) -> dict[str, object]:
    unique = uuid4().hex[:8]
    response = client.post(
        "/auth/users",
        json=admin_payload(
            email=f"{role_name.lower()}-{unique}@silentsepsis.test",
            staff_id=f"{role_name[:3].upper()}-{unique}",
            role_name=role_name,
        ),
        headers=auth_header(admin_token),
    )
    assert response.status_code == 201
    return response.json()


def create_ward(token: str) -> dict[str, object]:
    response = client.post(
        "/wards",
        json={"name": f"ICU-{uuid4().hex[:6]}", "capacity": 2},
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


def create_patient(token: str, ward_id: UUID) -> dict[str, object]:
    response = client.post(
        "/patients",
        json={
            "name": "Feedback Patient",
            "age": 50,
            "sex": "FEMALE",
            "ward_id": str(ward_id),
            "bed_number": "A1",
            "admission_date": "2026-08-07T08:00:00Z",
            "admission_reason": "Sepsis observation",
        },
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


def create_vital(token: str, patient_id: UUID) -> dict[str, object]:
    response = client.post(
        f"/patients/{patient_id}/vitals",
        json={
            "heart_rate": 100,
            "respiratory_rate": 24,
            "systolic_bp": 130,
            "diastolic_bp": 90,
            "spo2": 92.0,
            "temperature": 38.0,
            "recorded_at": datetime.now().isoformat(),
        },
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


class HighRiskPredictor(RiskPredictor):
    def predict(self, vitals, baseline):
        return PredictionResult(
            risk_score=0.95,
            risk_tier="CRITICAL",
            feature_contributions=[
                FeatureContribution(
                    feature_name="heart_rate",
                    contribution=0.95,
                    feature_value=vitals.heart_rate,
                )
            ],
        )


def create_alert(token: str) -> Alert:
    ward = create_ward(token)
    patient = create_patient(token, UUID(ward["id"]))
    vital = create_vital(token, UUID(patient["id"]))

    from app.services.prediction_service import PredictionService

    with SessionLocal() as db:
        PredictionService(HighRiskPredictor()).generate_prediction(
            db,
            UUID(patient["id"]),
            UUID(vital["id"]),
        )
        alert = db.scalar(select(Alert).where(Alert.patient_id == UUID(patient["id"])))
        assert alert is not None
        return alert


def test_physician_submits_feedback_on_alert() -> None:
    admin_token = bootstrap_admin()
    physician = create_user(admin_token, "Physician")
    physician_token = login(physician["email"])["access_token"]
    alert = create_alert(admin_token)

    response = client.post(
        f"/alerts/{alert.id}/feedback",
        json={"feedback_type": "CONFIRMED", "comments": "Clinically consistent"},
        headers=auth_header(physician_token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["alert_id"] == str(alert.id)
    assert body["clinician_id"] == physician["id"]
    assert body["feedback_type"] == "CONFIRMED"
    assert body["comments"] == "Clinically consistent"


def test_admin_submits_feedback_on_alert() -> None:
    admin_token = bootstrap_admin()
    alert = create_alert(admin_token)

    response = client.post(
        f"/alerts/{alert.id}/feedback",
        json={"feedback_type": "OTHER", "comments": None},
        headers=auth_header(admin_token),
    )

    assert response.status_code == 201
    assert response.json()["feedback_type"] == "OTHER"


def test_nurse_cannot_submit_feedback() -> None:
    admin_token = bootstrap_admin()
    nurse = create_user(admin_token, "Nurse")
    nurse_token = login(nurse["email"])["access_token"]
    alert = create_alert(admin_token)

    response = client.post(
        f"/alerts/{alert.id}/feedback",
        json={"feedback_type": "CONFIRMED"},
        headers=auth_header(nurse_token),
    )

    assert response.status_code == 403


def test_multiple_feedback_entries_persist_for_same_alert() -> None:
    admin_token = bootstrap_admin()
    physician = create_user(admin_token, "Physician")
    physician_token = login(physician["email"])["access_token"]
    alert = create_alert(admin_token)

    first = client.post(
        f"/alerts/{alert.id}/feedback",
        json={"feedback_type": "CONFIRMED", "comments": "First"},
        headers=auth_header(admin_token),
    )
    second = client.post(
        f"/alerts/{alert.id}/feedback",
        json={"feedback_type": "FALSE_POSITIVE", "comments": "Second"},
        headers=auth_header(physician_token),
    )

    assert first.status_code == 201
    assert second.status_code == 201
    with SessionLocal() as db:
        rows = list(db.scalars(select(Feedback).where(Feedback.alert_id == alert.id)))
        assert len(rows) == 2


def test_invalid_feedback_type_returns_422() -> None:
    admin_token = bootstrap_admin()
    alert = create_alert(admin_token)

    response = client.post(
        f"/alerts/{alert.id}/feedback",
        json={"feedback_type": "NOT_REAL"},
        headers=auth_header(admin_token),
    )

    assert response.status_code == 422


def test_feedback_on_nonexistent_alert_returns_404() -> None:
    admin_token = bootstrap_admin()

    response = client.post(
        f"/alerts/{uuid4()}/feedback",
        json={"feedback_type": "CONFIRMED"},
        headers=auth_header(admin_token),
    )

    assert response.status_code == 404


def test_get_feedback_list_returns_newest_first_for_any_role() -> None:
    admin_token = bootstrap_admin()
    nurse = create_user(admin_token, "Nurse")
    nurse_token = login(nurse["email"])["access_token"]
    alert = create_alert(admin_token)

    client.post(
        f"/alerts/{alert.id}/feedback",
        json={"feedback_type": "CONFIRMED", "comments": "Older"},
        headers=auth_header(admin_token),
    )
    client.post(
        f"/alerts/{alert.id}/feedback",
        json={"feedback_type": "OTHER", "comments": "Newer"},
        headers=auth_header(admin_token),
    )

    response = client.get(
        f"/alerts/{alert.id}/feedback",
        headers=auth_header(nurse_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["comments"] for item in body] == ["Newer", "Older"]


def test_feedback_requires_authentication() -> None:
    response = client.get(f"/alerts/{uuid4()}/feedback")
    assert response.status_code == 401
