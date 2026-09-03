from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.feedback import Feedback
from app.models.user import User
from app.schemas.feedback import FeedbackCreate
from app.services.audit_service import safe_record_audit_event


class FeedbackServiceError(Exception):
    message = "Feedback service error"


class AlertNotFoundError(FeedbackServiceError):
    message = "Alert not found"


def submit_feedback(
    db: Session,
    alert_id: UUID,
    user: User,
    data: FeedbackCreate,
) -> Feedback:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise AlertNotFoundError()

    feedback = Feedback(
        alert_id=alert.id,
        clinician_id=user.id,
        feedback_type=data.feedback_type,
        comments=data.comments,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    safe_record_audit_event(
        db,
        user,
        action="feedback_submitted",
        entity="alert",
        entity_id=alert.id,
    )
    return feedback


def get_feedback_for_alert(
    db: Session,
    alert_id: UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[Feedback]:
    if db.get(Alert, alert_id) is None:
        raise AlertNotFoundError()

    return list(
        db.scalars(
            select(Feedback)
            .where(Feedback.alert_id == alert_id)
            .order_by(Feedback.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
