from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.vital_reading import (
    VitalReadingBatchCreate,
    VitalReadingCreate,
    VitalReadingOut,
)
from app.services import vital_service
from app.services.patient_service import PatientNotFoundError


router = APIRouter(prefix="/patients", tags=["vitals"])


def _map_vital_error(error: Exception) -> HTTPException:
    if isinstance(error, PatientNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error.message,
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected vital service error",
    )


@router.post(
    "/{patient_id}/vitals",
    response_model=VitalReadingOut,
    status_code=status.HTTP_201_CREATED,
)
def record_vital(
    patient_id: UUID,
    payload: VitalReadingCreate,
    current_user: User = Depends(require_role("Admin", "Physician", "Nurse")),
    db: Session = Depends(get_db),
) -> VitalReadingOut:
    """Record a single physiological vital reading for a patient."""
    try:

        vital = vital_service.record_vital(db, patient_id, payload, current_user.id)
    except PatientNotFoundError as exc:
        raise _map_vital_error(exc) from exc
    return vital


@router.post(
    "/{patient_id}/vitals/batch",
    response_model=list[VitalReadingOut],
    status_code=status.HTTP_201_CREATED,
)
def record_vitals_batch(
    patient_id: UUID,
    payload: VitalReadingBatchCreate,
    current_user: User = Depends(require_role("Admin", "Physician", "Nurse")),
    db: Session = Depends(get_db),
) -> list[VitalReadingOut]:
    """Record a batch of vital readings for multiple patients."""
    if payload.patient_id != patient_id:

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Path patient_id must match body patient_id",
        )

    try:
        vitals = vital_service.record_vitals_batch(db, patient_id, payload, current_user.id)
    except PatientNotFoundError as exc:
        raise _map_vital_error(exc) from exc
    return vitals


@router.get("/{patient_id}/vitals", response_model=list[VitalReadingOut])
def get_vitals_history(
    patient_id: UUID,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[VitalReadingOut]:
    """Retrieve historical vital readings for a patient."""
    try:

        return vital_service.get_vitals_history(
            db,
            patient_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )
    except PatientNotFoundError as exc:
        raise _map_vital_error(exc) from exc


@router.get("/{patient_id}/vitals/latest", response_model=VitalReadingOut)
def get_latest_vital(
    patient_id: UUID,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VitalReadingOut:
    """Retrieve the most recent vital readings for a patient."""
    try:

        vital = vital_service.get_latest_vital(db, patient_id)
    except PatientNotFoundError as exc:
        raise _map_vital_error(exc) from exc
    if vital is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No vital readings found for this patient",
        )
    return vital
