from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.alert import AlertOut, AlertListItem, AlertDismissRequest
from app.services.alert_service import (
    AlertServiceError,
    AlertNotFoundError,
    InvalidTransitionError,
    DismissReasonMissingError,
    get_alerts,
    get_alert,
    acknowledge_alert,
    confirm_alert,
    dismiss_alert,
    resolve_alert,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AlertNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    if isinstance(exc, DismissReasonMissingError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message)
    if isinstance(exc, InvalidTransitionError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected alert service error")


@router.get("", response_model=list[AlertListItem])
def list_alerts(
    ward_id: UUID | None = Query(default=None),
    patient_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    alerts = get_alerts(db, ward_id=ward_id, patient_id=patient_id, status=status, limit=limit, offset=offset)
    return [AlertListItem.model_validate(a).model_dump() for a in alerts]


@router.get("/{alert_id}", response_model=AlertOut)
def read_alert(alert_id: UUID, _current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AlertOut:
    try:
        alert = get_alert(db, alert_id)
        return AlertOut.model_validate(alert).model_dump()
    except Exception as exc:
        raise _map_error(exc) from exc


@router.patch("/{alert_id}/acknowledge", dependencies=[Depends(require_role("Admin", "Physician", "Nurse"))], response_model=AlertOut)
def patch_acknowledge(alert_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AlertOut:
    try:
        alert = acknowledge_alert(db, alert_id, current_user)
        return AlertOut.model_validate(alert).model_dump()
    except Exception as exc:
        raise _map_error(exc) from exc


@router.patch("/{alert_id}/confirm", dependencies=[Depends(require_role("Admin", "Physician"))], response_model=AlertOut)
def patch_confirm(alert_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AlertOut:
    try:
        alert = confirm_alert(db, alert_id, current_user)
        return AlertOut.model_validate(alert).model_dump()
    except Exception as exc:
        raise _map_error(exc) from exc


@router.patch("/{alert_id}/dismiss", dependencies=[Depends(require_role("Admin", "Physician", "Nurse"))], response_model=AlertOut)
def patch_dismiss(alert_id: UUID, payload: AlertDismissRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AlertOut:
    try:
        alert = dismiss_alert(db, alert_id, current_user, payload.reason)
        return AlertOut.model_validate(alert).model_dump()
    except Exception as exc:
        raise _map_error(exc) from exc


@router.patch("/{alert_id}/resolve", dependencies=[Depends(require_role("Admin", "Physician"))], response_model=AlertOut)
def patch_resolve(alert_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AlertOut:
    try:
        alert = resolve_alert(db, alert_id, current_user)
        return AlertOut.model_validate(alert).model_dump()
    except Exception as exc:
        raise _map_error(exc) from exc
