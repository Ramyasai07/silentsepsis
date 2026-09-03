from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.alert import AlertDismissRequest, AlertListItem, AlertOut
from app.schemas.feedback import FeedbackCreate, FeedbackOut
from app.services.alert_service import (
    AlertNotFoundError,
    DismissReasonMissingError,
    InvalidTransitionError,
    acknowledge_alert,
    confirm_alert,
    dismiss_alert,
    get_alert,
    get_alerts,
    resolve_alert,
)
from app.services.feedback_service import (
    AlertNotFoundError as FeedbackAlertNotFoundError,
)
from app.services.feedback_service import (
    get_feedback_for_alert,
    submit_feedback,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AlertNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    if isinstance(exc, DismissReasonMissingError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
        )
    if isinstance(exc, InvalidTransitionError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected alert service error",
    )


def _map_feedback_error(exc: Exception) -> HTTPException:
    if isinstance(exc, FeedbackAlertNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected feedback service error",
    )


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
    """Retrieve alerts filtered by status, patient, or ward."""
    alerts = get_alerts(
        db,
        ward_id=ward_id,
        patient_id=patient_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [AlertListItem.model_validate(a).model_dump() for a in alerts]


@router.get("/{alert_id}", response_model=AlertOut)
def read_alert(
    alert_id: UUID,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertOut:
    """Retrieve details of a specific alert by ID."""
    try:
        alert = get_alert(db, alert_id)
        return AlertOut.model_validate(alert).model_dump()
    except Exception as exc:
        raise _map_error(exc) from exc


@router.patch(
    "/{alert_id}/acknowledge",
    dependencies=[Depends(require_role("Admin", "Physician", "Nurse"))],
    response_model=AlertOut,
)
def patch_acknowledge(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertOut:
    """Transition alert status to ACKNOWLEDGED."""
    try:
        alert = acknowledge_alert(db, alert_id, current_user)
        return AlertOut.model_validate(alert).model_dump()
    except Exception as exc:
        raise _map_error(exc) from exc


@router.patch(
    "/{alert_id}/confirm",
    dependencies=[Depends(require_role("Admin", "Physician"))],
    response_model=AlertOut,
)
def patch_confirm(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertOut:
    """Transition alert status to CONFIRMED."""
    try:
        alert = confirm_alert(db, alert_id, current_user)
        return AlertOut.model_validate(alert).model_dump()
    except Exception as exc:
        raise _map_error(exc) from exc


@router.patch(
    "/{alert_id}/dismiss",
    dependencies=[Depends(require_role("Admin", "Physician", "Nurse"))],
    response_model=AlertOut,
)
def patch_dismiss(
    alert_id: UUID,
    payload: AlertDismissRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertOut:
    """Dismiss an alert with a reason and optional comment."""
    try:
        alert = dismiss_alert(db, alert_id, current_user, payload.reason)
        return AlertOut.model_validate(alert).model_dump()
    except Exception as exc:
        raise _map_error(exc) from exc


@router.patch(
    "/{alert_id}/resolve",
    dependencies=[Depends(require_role("Admin", "Physician"))],
    response_model=AlertOut,
)
def patch_resolve(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertOut:
    """Resolve an alert after clinical action."""
    try:
        alert = resolve_alert(db, alert_id, current_user)
        return AlertOut.model_validate(alert).model_dump()
    except Exception as exc:
        raise _map_error(exc) from exc


@router.post(
    "/{alert_id}/feedback",
    status_code=status.HTTP_201_CREATED,
    response_model=FeedbackOut,
    tags=["feedback"],
)
def create_alert_feedback(
    alert_id: UUID,
    payload: FeedbackCreate,
    current_user: User = Depends(require_role("Admin", "Physician")),
    db: Session = Depends(get_db),
) -> FeedbackOut:
    """Submit clinician feedback on a specific alert."""
    try:
        feedback = submit_feedback(db, alert_id, current_user, payload)
    except Exception as exc:
        raise _map_feedback_error(exc) from exc
    return FeedbackOut.model_validate(feedback).model_dump()


@router.get("/{alert_id}/feedback", response_model=list[FeedbackOut], tags=["feedback"])
def list_alert_feedback(
    alert_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FeedbackOut]:
    """List all feedback submissions for a specific alert."""
    try:
        feedback = get_feedback_for_alert(
            db,
            alert_id,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        raise _map_feedback_error(exc) from exc
    return [FeedbackOut.model_validate(item).model_dump() for item in feedback]
