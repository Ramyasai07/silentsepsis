from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.patient import (
    PatientBaselineCreate,
    PatientBaselineOut,
    PatientCreate,
    PatientListItem,
    PatientOut,
    PatientUpdate,
)
from app.services import patient_service
from app.services.audit_service import safe_record_audit_event
from app.services.patient_service import (
    BaselineNotFoundError,
    DuplicateBedNumberError,
    PatientNotFoundError,
    WardCapacityExceededError,
    WardNotFoundError,
)

router = APIRouter(prefix="/patients", tags=["patients"])


def _map_patient_error(error: Exception) -> HTTPException:
    if isinstance(error, (PatientNotFoundError, BaselineNotFoundError)):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=error.message
        )
    if isinstance(error, WardNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=error.message
        )
    if isinstance(error, (WardCapacityExceededError, DuplicateBedNumberError)):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error.message)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected patient service error",
    )


@router.post(
    "",
    response_model=PatientOut,
    status_code=status.HTTP_201_CREATED,
)
def create_patient(
    payload: PatientCreate,
    current_user: User = Depends(require_role("Admin", "Physician")),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Register a new patient in a ward."""
    try:
        patient = patient_service.create_patient(db, payload)
    except (
        WardNotFoundError,
        WardCapacityExceededError,
        DuplicateBedNumberError,
    ) as exc:
        raise _map_patient_error(exc) from exc
    safe_record_audit_event(
        db,
        current_user,
        action="patient_created",
        entity="patient",
        entity_id=patient.id,
    )
    return patient_service.to_patient_out(patient)


@router.get("", response_model=list[PatientListItem])
def list_patients(
    ward_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    """List registered patients, optionally filtered by ward."""
    try:
        return patient_service.get_patients(
            db,
            ward_id=ward_id,
            limit=limit,
            offset=offset,
        )
    except WardNotFoundError as exc:
        raise _map_patient_error(exc) from exc


@router.get("/{patient_id}", response_model=PatientOut)
def read_patient(
    patient_id: UUID,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Retrieve details of a specific patient profile by ID."""
    try:
        patient = patient_service.get_patient(db, patient_id)
    except PatientNotFoundError as exc:
        raise _map_patient_error(exc) from exc
    return patient_service.to_patient_out(patient)


@router.patch(
    "/{patient_id}",
    response_model=PatientOut,
)
def update_patient(
    patient_id: UUID,
    payload: PatientUpdate,
    current_user: User = Depends(require_role("Admin", "Physician")),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Update patient demographic or location details."""
    try:
        patient = patient_service.update_patient(db, patient_id, payload)
    except (
        PatientNotFoundError,
        WardNotFoundError,
        WardCapacityExceededError,
        DuplicateBedNumberError,
    ) as exc:
        raise _map_patient_error(exc) from exc
    safe_record_audit_event(
        db,
        current_user,
        action="patient_updated",
        entity="patient",
        entity_id=patient.id,
    )
    return patient_service.to_patient_out(patient)


@router.post(
    "/{patient_id}/baseline",
    response_model=PatientBaselineOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("Admin", "Physician"))],
)
def set_patient_baseline(
    patient_id: UUID,
    payload: PatientBaselineCreate,
    db: Session = Depends(get_db),
) -> PatientBaselineOut:
    """Set or update clinical baseline values for a patient."""
    try:
        baseline = patient_service.set_patient_baseline(db, patient_id, payload)
    except PatientNotFoundError as exc:
        raise _map_patient_error(exc) from exc
    return PatientBaselineOut.model_validate(baseline)


@router.get("/{patient_id}/baseline", response_model=PatientBaselineOut)
def read_patient_baseline(
    patient_id: UUID,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PatientBaselineOut:
    """Retrieve clinical baseline values for a patient."""
    try:
        baseline = patient_service.get_patient_baseline(db, patient_id)
    except (PatientNotFoundError, BaselineNotFoundError) as exc:
        raise _map_patient_error(exc) from exc
    return PatientBaselineOut.model_validate(baseline)
