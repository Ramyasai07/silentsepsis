from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.ml.rule_based_predictor import RuleBasedPredictor
from app.models.user import User
from app.schemas.prediction import PredictionCreate, PredictionOut
from app.services.prediction_service import (
    NoVitalReadingsError,
    PatientNotFoundError,
    PredictionNotFoundError,
    PredictionService,
    VitalReadingNotFoundError,
)

router = APIRouter(prefix="/patients/{patient_id}/predictions", tags=["predictions"])


def get_prediction_service() -> PredictionService:
    return PredictionService(RuleBasedPredictor())


def _map_prediction_error(error: Exception) -> HTTPException:
    if isinstance(
        error,
        (PatientNotFoundError, VitalReadingNotFoundError, PredictionNotFoundError),
    ):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=error.message
        )
    if isinstance(error, NoVitalReadingsError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error.message)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected prediction service error",
    )


@router.post(
    "",
    response_model=PredictionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("Admin", "Physician", "Nurse"))],
)
def create_prediction(
    patient_id: UUID,
    payload: PredictionCreate,
    db: Session = Depends(get_db),
    prediction_service: PredictionService = Depends(get_prediction_service),
) -> PredictionOut:
    """Record a new risk prediction evaluation."""
    if payload.patient_id != patient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient ID in body does not match path parameter",
        )

    try:
        prediction = prediction_service.generate_prediction(
            db,
            patient_id=patient_id,
            vital_reading_id=payload.vital_reading_id,
        )
    except Exception as exc:
        raise _map_prediction_error(exc) from exc

    return PredictionOut.model_validate(prediction).model_dump()


@router.get("", response_model=list[PredictionOut])
def list_predictions(
    patient_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    prediction_service: PredictionService = Depends(get_prediction_service),
) -> list[PredictionOut]:
    """List historical risk predictions for a patient."""
    try:
        predictions = prediction_service.get_predictions_for_patient(
            db,
            patient_id=patient_id,
            limit=limit,
            offset=offset,
        )
        return [PredictionOut.model_validate(pred).model_dump() for pred in predictions]
    except Exception as exc:
        raise _map_prediction_error(exc) from exc


@router.get("/latest", response_model=PredictionOut)
def read_latest_prediction(
    patient_id: UUID,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    prediction_service: PredictionService = Depends(get_prediction_service),
) -> PredictionOut:
    """Retrieve the most recent risk prediction for a patient."""
    try:
        prediction = prediction_service.get_latest_prediction(db, patient_id=patient_id)
        return PredictionOut.model_validate(prediction).model_dump()
    except Exception as exc:
        raise _map_prediction_error(exc) from exc
