from datetime import datetime
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from celery.exceptions import Retry
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.ml.base import FeatureContribution, PredictionResult, RiskPredictor
from app.models.patient import Patient
from app.models.prediction import Prediction
from app.models.vital_reading import VitalReading
from app.models.ward import Ward
from app.tasks.risk_evaluation import evaluate_all_active_patients

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def migrate_database() -> None:
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(autouse=True)
def clean_data() -> None:
    with SessionLocal() as db:
        db.execute(delete(Prediction))
        db.execute(delete(VitalReading))
        db.execute(delete(Patient))
        db.execute(delete(Ward))
        db.commit()
    yield
    with SessionLocal() as db:
        db.execute(delete(Prediction))
        db.execute(delete(VitalReading))
        db.execute(delete(Patient))
        db.execute(delete(Ward))
        db.commit()


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


def bootstrap_admin() -> str:
    response = client.post(
        "/auth/bootstrap",
        json=admin_payload(),
        headers=bootstrap_secret_header(),
    )
    if response.status_code == 201:
        return login("admin@silentsepsis.test", "StrongPass123")["access_token"]
    assert response.status_code == 403
    return login("admin@silentsepsis.test", "StrongPass123")["access_token"]


def create_ward(token: str) -> dict[str, object]:
    response = client.post(
        "/wards",
        json={"name": "ICU", "capacity": 2},
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


def create_patient(
    token: str, ward_id: UUID, bed_number: str = "A1"
) -> dict[str, object]:
    response = client.post(
        "/patients",
        json={
            "name": "Test Patient",
            "age": 50,
            "sex": "FEMALE",
            "ward_id": str(ward_id),
            "bed_number": bed_number,
            "admission_date": "2026-08-07T08:00:00Z",
            "admission_reason": "Observation",
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
                FeatureContribution(feature_name="heart_rate", contribution=0.95)
            ],
        )


def test_evaluate_all_active_patients_creates_prediction_for_patient_with_vitals() -> (
    None
):
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))
    create_vital(admin_token, UUID(patient["id"]))

    with patch("app.tasks.risk_evaluation.RuleBasedPredictor", new=HighRiskPredictor):
        result = evaluate_all_active_patients.apply().get()

    assert result["patients_evaluated"] == 1
    assert result["predictions_created"] == 1
    assert result["errors"] == 0

    with SessionLocal() as db:
        prediction_count = db.scalar(
            select(func.count())
            .select_from(Prediction)
            .where(Prediction.patient_id == UUID(patient["id"]))
        )
        assert prediction_count == 1


def test_evaluate_all_active_patients_skips_patients_with_no_vitals() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    create_patient(admin_token, UUID(ward["id"]), bed_number="A1")
    patient_with_vitals = create_patient(admin_token, UUID(ward["id"]), bed_number="A2")
    create_vital(admin_token, UUID(patient_with_vitals["id"]))

    with patch("app.tasks.risk_evaluation.RuleBasedPredictor", new=HighRiskPredictor):
        result = evaluate_all_active_patients.apply().get()

    assert result["patients_evaluated"] == 1
    assert result["predictions_created"] == 1
    assert result["errors"] == 0


def test_individual_patient_failure_does_not_stop_next_patient() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient1 = create_patient(admin_token, UUID(ward["id"]), bed_number="A1")
    patient2 = create_patient(admin_token, UUID(ward["id"]), bed_number="A2")
    create_vital(admin_token, UUID(patient1["id"]))
    create_vital(admin_token, UUID(patient2["id"]))

    original_generate = None
    from app.services.prediction_service import PredictionService

    def side_effect(self, db, patient_id, vital_reading_id=None):
        if str(patient_id) == str(patient1["id"]):
            raise RuntimeError("forced business failure")
        return original_generate(
            self, db, patient_id, vital_reading_id=vital_reading_id
        )

    original_generate = PredictionService.generate_prediction
    with (
        patch("app.tasks.risk_evaluation.RuleBasedPredictor", new=HighRiskPredictor),
        patch(
            "app.tasks.risk_evaluation.PredictionService.generate_prediction",
            new=side_effect,
        ),
    ):
        result = evaluate_all_active_patients.apply().get()

    assert result["patients_evaluated"] == 2
    assert result["predictions_created"] == 1
    assert result["errors"] == 1


def test_business_failure_does_not_retry_batch() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))
    create_vital(admin_token, UUID(patient["id"]))

    def raise_business_failure(self, db, patient_id, vital_reading_id=None):
        raise RuntimeError("forced business failure")

    with (
        patch("app.tasks.risk_evaluation.RuleBasedPredictor", new=HighRiskPredictor),
        patch(
            "app.tasks.risk_evaluation.PredictionService.generate_prediction",
            new=raise_business_failure,
        ),
        patch.object(evaluate_all_active_patients, "retry") as mocked_retry,
    ):
        result = evaluate_all_active_patients.apply().get()

    assert result["patients_evaluated"] == 1
    assert result["predictions_created"] == 0
    assert result["errors"] == 1
    mocked_retry.assert_not_called()


def test_evaluate_all_active_patients_handles_patient_deleted_before_evaluation() -> (
    None
):
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)

    patient1 = create_patient(
        admin_token,
        UUID(ward["id"]),
        bed_number="A1",
    )
    patient2 = create_patient(
        admin_token,
        UUID(ward["id"]),
        bed_number="A2",
    )

    create_vital(admin_token, UUID(patient1["id"]))
    create_vital(admin_token, UUID(patient2["id"]))

    from app.services.prediction_service import PredictionService

    original_generate = PredictionService.generate_prediction

    def generate_with_patient_removed(
        self,
        db,
        patient_id,
        vital_reading_id=None,
    ):
        if str(patient_id) == str(patient1["id"]):
            with SessionLocal() as cleanup_db:
                cleanup_db.execute(delete(Patient).where(Patient.id == patient_id))
                cleanup_db.commit()

        return original_generate(
            self,
            db,
            patient_id,
            vital_reading_id=vital_reading_id,
        )

    with (
        patch(
            "app.tasks.risk_evaluation.RuleBasedPredictor",
            new=HighRiskPredictor,
        ),
        patch.object(
            PredictionService,
            "generate_prediction",
            new=generate_with_patient_removed,
        ),
    ):
        result = evaluate_all_active_patients.apply().get()

    assert result["patients_evaluated"] == 2
    assert result["predictions_created"] == 1
    assert result["errors"] == 1


def test_transient_db_error_triggers_retry() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))
    create_vital(admin_token, UUID(patient["id"]))

    def raise_operational_error(self, db, patient_id, vital_reading_id=None):
        raise OperationalError("SELECT 1", {}, Exception("transient"))

    with (
        patch("app.tasks.risk_evaluation.RuleBasedPredictor", new=HighRiskPredictor),
        patch(
            "app.tasks.risk_evaluation.PredictionService.generate_prediction",
            new=raise_operational_error,
        ),
        patch.object(
            evaluate_all_active_patients,
            "retry",
            side_effect=Retry("forced retry"),
        ) as mocked_retry,
    ):
        with pytest.raises(Retry):
            evaluate_all_active_patients.run()

    mocked_retry.assert_called_once()
    retry_kwargs = mocked_retry.call_args.kwargs["kwargs"]
    assert retry_kwargs["processed_patient_ids"] == []
    assert retry_kwargs["patient_ids_to_evaluate"] == [patient["id"]]
    assert retry_kwargs["retrying_patient_id"] == patient["id"]
    assert retry_kwargs["patients_evaluated"] == 1
    assert retry_kwargs["predictions_created"] == 0
    assert retry_kwargs["errors"] == 0


def test_transient_db_error_retry_state_preserves_completed_work() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient1 = create_patient(admin_token, UUID(ward["id"]), bed_number="A1")
    patient2 = create_patient(admin_token, UUID(ward["id"]), bed_number="A2")
    create_vital(admin_token, UUID(patient1["id"]))
    create_vital(admin_token, UUID(patient2["id"]))

    from app.services.prediction_service import PredictionService

    original_generate = PredictionService.generate_prediction

    def fail_second_patient(self, db, patient_id, vital_reading_id=None):
        if str(patient_id) == str(patient2["id"]):
            raise OperationalError("SELECT 1", {}, Exception("transient"))
        return original_generate(
            self,
            db,
            patient_id,
            vital_reading_id=vital_reading_id,
        )

    with (
        patch(
            "app.tasks.risk_evaluation.RuleBasedPredictor",
            new=HighRiskPredictor,
        ),
        patch(
            "app.tasks.risk_evaluation.PredictionService.generate_prediction",
            new=fail_second_patient,
        ),
        patch.object(
            evaluate_all_active_patients,
            "retry",
            side_effect=Retry("forced retry"),
        ) as mocked_retry,
    ):
        with pytest.raises(Retry):
            evaluate_all_active_patients.run(
                patient_ids_to_evaluate=[
                    patient1["id"],
                    patient2["id"],
                ]
            )

    mocked_retry.assert_called_once()

    retry_kwargs = mocked_retry.call_args.kwargs["kwargs"]

    assert retry_kwargs["processed_patient_ids"] == []
    assert retry_kwargs["patient_ids_to_evaluate"] == [patient2["id"]]
    assert retry_kwargs["retrying_patient_id"] == patient2["id"]
    assert retry_kwargs["patients_evaluated"] == 2
    assert retry_kwargs["predictions_created"] == 1
    assert retry_kwargs["errors"] == 0


def test_transient_db_retry_reattempts_failed_patient_without_double_counting() -> None:
    admin_token = bootstrap_admin()
    ward = create_ward(admin_token)
    patient = create_patient(admin_token, UUID(ward["id"]))
    create_vital(admin_token, UUID(patient["id"]))

    with patch("app.tasks.risk_evaluation.RuleBasedPredictor", new=HighRiskPredictor):
        result = evaluate_all_active_patients.apply(
            kwargs={
                "patient_ids_to_evaluate": [patient["id"]],
                "retrying_patient_id": patient["id"],
                "patients_evaluated": 1,
            }
        ).get()

    assert result["patients_evaluated"] == 1
    assert result["predictions_created"] == 1
    assert result["errors"] == 0


def test_trigger_risk_evaluation_endpoint_enqueues_task() -> None:
    admin_token = bootstrap_admin()

    with patch("app.api.v1.tasks.evaluate_all_active_patients.delay") as mocked_delay:
        mocked_delay.return_value.id = "task-id-123"
        response = client.post(
            "/admin/tasks/evaluate-risk",
            headers=auth_header(admin_token),
        )

    assert response.status_code == 202
    assert response.json() == {"task_id": "task-id-123"}
    mocked_delay.assert_called_once_with()


def test_trigger_risk_evaluation_endpoint_forbidden_for_non_admin() -> None:
    admin_token = bootstrap_admin()
    nurse_email = f"nurse-{uuid4().hex[:8]}@silentsepsis.test"
    response = client.post(
        "/auth/users",
        json={
            "email": nurse_email,
            "staff_id": f"NUR-{uuid4().hex[:8]}",
            "full_name": "Nurse User",
            "password": "StrongPass123",
            "role_name": "Nurse",
        },
        headers=auth_header(admin_token),
    )
    assert response.status_code == 201
    nurse = response.json()
    nurse_token = login(nurse["email"])["access_token"]

    response = client.post(
        "/admin/tasks/evaluate-risk",
        headers=auth_header(nurse_token),
    )
    assert response.status_code == 403
