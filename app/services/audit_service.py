"""Explicit audit logging helpers.

Audit writes are best-effort: failures are logged and must never break the
primary clinical or administrative action that triggered them.
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User

logger = logging.getLogger(__name__)


class AuditLogNotFoundError(Exception):
    message = "Audit log not found"


def record_audit_event(
    db: Session,
    user: User | None,
    action: str,
    entity: str,
    entity_id: UUID | None,
    ip_address: str | None = None,
) -> AuditLog | None:
    try:
        audit_log = AuditLog(
            user_id=user.id if user is not None else None,
            action=action,
            entity=entity,
            entity_id=entity_id,
            ip_address=ip_address,
        )
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        return audit_log
    except Exception:
        db.rollback()
        logger.exception(
            "Audit logging failed for action=%s entity=%s entity_id=%s",
            action,
            entity,
            entity_id,
        )
        return None


def safe_record_audit_event(
    db: Session,
    user: User | None,
    action: str,
    entity: str,
    entity_id: UUID | None,
    ip_address: str | None = None,
) -> AuditLog | None:
    try:
        return record_audit_event(db, user, action, entity, entity_id, ip_address)
    except Exception:
        db.rollback()
        logger.exception(
            "Audit logging call failed for action=%s entity=%s entity_id=%s",
            action,
            entity,
            entity_id,
        )
        return None


def get_audit_logs(
    db: Session,
    *,
    entity: str | None = None,
    entity_id: UUID | None = None,
    user_id: UUID | None = None,
    action: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AuditLog]:
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    if entity is not None:
        query = query.where(AuditLog.entity == entity)
    if entity_id is not None:
        query = query.where(AuditLog.entity_id == entity_id)
    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
    if action is not None:
        query = query.where(AuditLog.action == action)
    return list(db.scalars(query.limit(limit).offset(offset)).all())


def get_audit_log(db: Session, audit_log_id: UUID) -> AuditLog:
    audit_log = db.get(AuditLog, audit_log_id)
    if audit_log is None:
        raise AuditLogNotFoundError()
    return audit_log
