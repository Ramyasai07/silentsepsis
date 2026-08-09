from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml.base import RiskPredictor
from app.models.patient import Patient
from app.models.patient_baseline import PatientBaseline
from app.models.prediction import Prediction, RiskLevel
from app.models.prediction_feature import PredictionFeature
from app.models.vital_reading import VitalReading


class PredictionServiceError(Exception):
    message = "Prediction service error"


class PatientNotFoundError(PredictionServiceError):
    message = "Patient not found"


class VitalReadingNotFoundError(PredictionServiceError):
    message = "Vital reading not found"


class NoVitalReadingsError(PredictionServiceError):
    message = "Patient has no vital readings"


class PredictionNotFoundError(PredictionServiceError):
    message = "Prediction not found"


class PredictionService:
    def __init__(self, predictor: RiskPredictor):
        self.predictor = predictor

    def generate_prediction(
        self,
        db: Session,
        patient_id: UUID,
        vital_reading_id: UUID | None = None,
    ) -> Prediction:
        patient = db.get(Patient, patient_id)
        if patient is None:
            raise PatientNotFoundError()

        if vital_reading_id is not None:
            vital = db.get(VitalReading, vital_reading_id)
            if vital is None or vital.patient_id != patient_id:
                raise VitalReadingNotFoundError()
        else:
            vital = db.scalar(
                select(VitalReading)
                .where(VitalReading.patient_id == patient_id)
                .order_by(VitalReading.recorded_at.desc())
                .limit(1)
            )
            if vital is None:
                raise NoVitalReadingsError()

        baseline = db.scalar(
            select(PatientBaseline).where(PatientBaseline.patient_id == patient_id)
        )
        prediction_result = self.predictor.predict(vital, baseline)

        prediction = Prediction(
            patient_id=patient_id,
            vital_reading_id=vital.id,
            model_version="rule-based-v1",
            risk_probability=prediction_result.risk_score,
            risk_level=RiskLevel(prediction_result.risk_tier),
            generated_at=datetime.now(timezone.utc),
        )

        try:
            db.add(prediction)
            db.flush()
            features = [
                PredictionFeature(
                    prediction_id=prediction.id,
                    feature_name=feature.feature_name,
                    feature_value=feature.feature_value,
                    contribution=feature.contribution,
                )
                for feature in prediction_result.feature_contributions
            ]
            db.add_all(features)
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(prediction)
        return prediction

    def get_predictions_for_patient(
        self,
        db: Session,
        patient_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Prediction]:
        patient = db.get(Patient, patient_id)
        if patient is None:
            raise PatientNotFoundError()

        return list(
            db.scalars(
                select(Prediction)
                .where(Prediction.patient_id == patient_id)
                .order_by(Prediction.generated_at.desc())
                .limit(limit)
                .offset(offset)
            ).all()
        )

    def get_latest_prediction(self, db: Session, patient_id: UUID) -> Prediction:
        patient = db.get(Patient, patient_id)
        if patient is None:
            raise PatientNotFoundError()

        prediction = db.scalar(
            select(Prediction)
            .where(Prediction.patient_id == patient_id)
            .order_by(Prediction.generated_at.desc())
            .limit(1)
        )
        if prediction is None:
            raise PredictionNotFoundError()
        return prediction
