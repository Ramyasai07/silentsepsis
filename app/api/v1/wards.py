from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.ward import WardCreate, WardOut, WardSummaryOut
from app.services import ward_service
from app.services.audit_service import safe_record_audit_event
from app.services.ward_service import WardNotFoundError


router = APIRouter(prefix="/wards", tags=["wards"])


def _map_ward_error(error: Exception) -> HTTPException:
    if isinstance(error, WardNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.message)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected ward service error",
    )


@router.post(
    "",
    response_model=WardOut,
    status_code=status.HTTP_201_CREATED,
)
def create_ward(
    payload: WardCreate,
    current_user: User = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Create a new hospital ward configuration."""
    ward = ward_service.create_ward(db, payload)

    safe_record_audit_event(
        db,
        current_user,
        action="ward_created",
        entity="ward",
        entity_id=ward.id,
    )
    return ward_service.to_ward_out(ward)


@router.get("", response_model=list[WardOut])
def list_wards(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    """List all configured hospital wards."""
    return [ward_service.to_ward_out(ward) for ward in ward_service.get_wards(db)]



@router.get("/{ward_id}", response_model=WardOut)
def read_ward(
    ward_id: UUID,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Retrieve details of a specific ward by ID."""
    try:

        ward = ward_service.get_ward(db, ward_id)
    except WardNotFoundError as exc:
        raise _map_ward_error(exc) from exc
    return ward_service.to_ward_out(ward)


@router.get("/{ward_id}/summary", response_model=WardSummaryOut)
def read_ward_summary(
    ward_id: UUID,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Retrieve occupancy and alert summary statistics for a ward."""
    try:

        return ward_service.get_summary(db, ward_id)
    except WardNotFoundError as exc:
        raise _map_ward_error(exc) from exc
