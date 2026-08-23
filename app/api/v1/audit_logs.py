from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.schemas.audit_log import AuditLogOut
from app.services.audit_service import (
    AuditLogNotFoundError,
    get_audit_log,
    get_audit_logs,
)

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


def _map_audit_error(error: Exception) -> HTTPException:
    if isinstance(error, AuditLogNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.message)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected audit log service error",
    )


@router.get(
    "",
    response_model=list[AuditLogOut],
    dependencies=[Depends(require_role("Admin"))],
)
def list_audit_logs(
    entity: str | None = None,
    entity_id: UUID | None = None,
    user_id: UUID | None = None,
    action: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[AuditLogOut]:
    """List audit log events with filtering."""

    logs = get_audit_logs(
        db,
        entity=entity,
        entity_id=entity_id,
        user_id=user_id,
        action=action,
        limit=limit,
        offset=offset,
    )
    return [AuditLogOut.model_validate(log).model_dump() for log in logs]


@router.get(
    "/{audit_log_id}",
    response_model=AuditLogOut,
    dependencies=[Depends(require_role("Admin"))],
)
def read_audit_log(
    audit_log_id: UUID,
    db: Session = Depends(get_db),
) -> AuditLogOut:
    """Retrieve a specific audit log entry by ID."""
    try:

        audit_log = get_audit_log(db, audit_log_id)
    except AuditLogNotFoundError as exc:
        raise _map_audit_error(exc) from exc
    return AuditLogOut.model_validate(audit_log).model_dump()
