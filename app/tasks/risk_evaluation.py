import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.metrics import CELERY_TASK_FAILURE_TOTAL, CELERY_TASK_SUCCESS_TOTAL
from app.db.session import SessionLocal
from app.ml.online_logistic_predictor import OnlineLogisticPredictor
from app.models.patient import Patient
from app.models.vital_reading import VitalReading
from app.services.prediction_service import PredictionService
from app.services.ward_service import ACTIVE_PATIENT_STATUSES
from app.tasks.celery_app import celery_app

RuleBasedPredictor = OnlineLogisticPredictor

logger = logging.getLogger(__name__)

_TASK_NAME = "evaluate_all_active_patients"


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks.risk_evaluation.evaluate_all_active_patients",
)
def evaluate_all_active_patients(
    self,
    processed_patient_ids: list[str] | None = None,
    patient_ids_to_evaluate: list[str] | None = None,
    retrying_patient_id: str | None = None,
    patients_evaluated: int = 0,
    predictions_created: int = 0,
    errors: int = 0,
) -> dict[str, int]:
    processed_patient_ids = processed_patient_ids or []

    if patient_ids_to_evaluate is None:
        db: Session = SessionLocal()
        try:
            vitals_exist = (
                select(VitalReading.id)
                .where(VitalReading.patient_id == Patient.id)
                .exists()
            )

            patient_ids = list(
                db.scalars(
                    select(Patient.id).where(
                        Patient.current_status.in_(ACTIVE_PATIENT_STATUSES),
                        vitals_exist,
                    )
                ).all()
            )
        finally:
            db.close()
    else:
        patient_ids = [UUID(patient_id) for patient_id in patient_ids_to_evaluate]

    logger.info(
        "Found %d active patients with vitals to evaluate",
        len(patient_ids),
    )

    # A patient that is active and has vitals when the batch selection runs may be
    # deleted before its individual prediction is committed. This race is handled
    # on a per-patient basis below: failures are logged, counted, and evaluation
    # continues for other patients.
    for index, patient_id in enumerate(patient_ids):
        if str(patient_id) in processed_patient_ids:
            continue

        if str(patient_id) == retrying_patient_id:
            retrying_patient_id = None
        else:
            patients_evaluated += 1

        logger.info("Evaluating risk for patient %s", patient_id)

        patient_db: Session = SessionLocal()

        try:
            PredictionService(RuleBasedPredictor()).generate_prediction(
                patient_db,
                patient_id,
            )

            predictions_created += 1
            processed_patient_ids.append(str(patient_id))

        except OperationalError as exc:
            patient_db.rollback()

            remaining_patient_ids = [
                str(patient_id),
                *[str(remaining_id) for remaining_id in patient_ids[index + 1 :]],
            ]

            logger.warning(
                "Transient DB error evaluating patient %s, retrying specific unit...",
                patient_id,
                exc_info=exc,
            )

            raise self.retry(
                exc=exc,
                countdown=2**self.request.retries,
                kwargs={
                    "processed_patient_ids": [],
                    "patient_ids_to_evaluate": remaining_patient_ids,
                    "retrying_patient_id": str(patient_id),
                    "patients_evaluated": patients_evaluated,
                    "predictions_created": predictions_created,
                    "errors": errors,
                },
            )

        except Exception as exc:
            patient_db.rollback()
            errors += 1
            processed_patient_ids.append(str(patient_id))

            logger.exception(
                "Risk evaluation failed for patient %s",
                patient_id,
                exc_info=exc,
            )

        finally:
            patient_db.close()

    summary = {
        "patients_evaluated": patients_evaluated,
        "predictions_created": predictions_created,
        "errors": errors,
    }

    logger.info("Risk evaluation summary: %s", summary)

    # Wire Celery metrics at the existing return point without restructuring.
    if errors > 0:
        CELERY_TASK_FAILURE_TOTAL.labels(task_name=_TASK_NAME).inc(errors)
    if predictions_created > 0:
        CELERY_TASK_SUCCESS_TOTAL.labels(task_name=_TASK_NAME).inc(predictions_created)

    return summary
