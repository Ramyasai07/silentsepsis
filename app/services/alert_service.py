from datetime import datetime, timezone
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertStatus, AlertSeverity
from app.models.user import User
from app.models.patient import Patient
from app.services.audit_service import safe_record_audit_event


class AlertServiceError(Exception):
    message = "Alert service error"


class AlertNotFoundError(AlertServiceError):
    message = "Alert not found"


class InvalidTransitionError(AlertServiceError):
    message = "Invalid alert state transition"


class DismissReasonMissingError(AlertServiceError):
    message = "Dismiss reason is required"


# Central state machine mapping: action -> { allowed_current_state: next_state }
STATE_TRANSITIONS: dict[str, dict[str, str]] = {
    "acknowledge": {"active": "watching"},
    "dismiss": {"active": "dismissed", "watching": "dismissed"},
    "confirm": {"watching": "confirmed"},
    "resolve": {"confirmed": "resolved"},
}

AUDIT_ACTIONS = {
    "acknowledge": "alert_acknowledged",
    "confirm": "alert_confirmed",
    "dismiss": "alert_dismissed",
    "resolve": "alert_resolved",
}


def evaluate_and_create_alert(db: Session, prediction) -> Alert | None:
    """
    Evaluate a prediction and create an Alert synchronously if it meets trigger tiers.

    Trigger tiers: HIGH and CRITICAL (reuse prediction.risk_tier values).
    Duplicate prevention: do not create a new alert if the patient already has an open alert
    (status in active, watching, confirmed).
    """
    trigger_tiers = {"HIGH", "CRITICAL"}
    if prediction.risk_tier not in trigger_tiers:
        return None

    # Compare enum labels case-insensitively in SQL to avoid SQLAlchemy enum-name/value binding differences
    open_statuses_lc = ["active", "watching", "confirmed"]

    existing = db.scalar(
        select(Alert).where(
            Alert.patient_id == prediction.patient_id,
            sa.func.lower(sa.cast(Alert.status, sa.Text)).in_(open_statuses_lc),
        )
    )
    if existing is not None:
        return None

    # Severity mapping: use prediction.risk_tier as-is when possible
    try:
        severity = AlertSeverity[prediction.risk_tier]
    except Exception:
        # Fallback: map CRITICAL/HIGH to CRITICAL/HIGH
        severity = AlertSeverity.CRITICAL if prediction.risk_tier == "CRITICAL" else AlertSeverity.HIGH

    message = f"Auto-alert from prediction: tier={prediction.risk_tier} score={prediction.risk_score:.3f}"

    alert = Alert(
        patient_id=prediction.patient_id,
        prediction_id=prediction.id,
        severity=severity,
        # Store the enum *value* (string) to avoid SQLAlchemy using enum member names
        status=AlertStatus.ACTIVE.value,
        message=message,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def get_alerts(
    db: Session,
    *,
    ward_id: UUID | None = None,
    patient_id: UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Alert]:
    query = select(Alert).order_by(Alert.created_at.desc())
    if ward_id is not None:
        query = query.join(Alert.patient).where(Patient.ward_id == ward_id)
    if patient_id is not None:
        query = query.where(Alert.patient_id == patient_id)
    if status is not None:
        # Compare case-insensitively to avoid enum label case mismatches between DB and runtime
        query = query.where(sa.func.lower(sa.cast(Alert.status, sa.Text)) == status.lower())

    return list(db.scalars(query.limit(limit).offset(offset)).all())


def get_alert(db: Session, alert_id: UUID) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise AlertNotFoundError()
    return alert


def _perform_transition(db: Session, alert: Alert, action: str, user: User, *, reason: str | None = None) -> Alert:
    current = alert.status.value if hasattr(alert.status, "value") else alert.status
    allowed = STATE_TRANSITIONS.get(action, {})
    if current not in allowed:
        err = InvalidTransitionError()
        err.message = f"Cannot perform action '{action}' from state '{current}'"
        raise err

    next_state = allowed[current]

    now = datetime.now(timezone.utc)

    if action == "acknowledge":
        # store string value to avoid enum-name/value binding issues
        alert.status = AlertStatus(next_state).value
        alert.acknowledged_by = user.id
        alert.acknowledged_at = now
    elif action == "confirm":
        alert.status = AlertStatus(next_state).value
        alert.confirmed_by = user.id
        alert.confirmed_at = now
    elif action == "dismiss":
        if not reason or not reason.strip():
            raise DismissReasonMissingError()
        alert.status = AlertStatus(next_state).value
        alert.dismissed_by = user.id
        alert.dismissed_at = now
        alert.dismissed_reason = reason
    elif action == "resolve":
        alert.status = AlertStatus(next_state).value
        alert.resolved_by = user.id
        alert.resolved_at = now
    else:
        err = InvalidTransitionError()
        err.message = f"Unknown action '{action}'"
        raise err

    db.commit()
    db.refresh(alert)
    safe_record_audit_event(
        db,
        user,
        action=AUDIT_ACTIONS[action],
        entity="alert",
        entity_id=alert.id,
    )
    return alert


def acknowledge_alert(db: Session, alert_id: UUID, user: User) -> Alert:
    alert = get_alert(db, alert_id)
    return _perform_transition(db, alert, "acknowledge", user)


def confirm_alert(db: Session, alert_id: UUID, user: User) -> Alert:
    alert = get_alert(db, alert_id)
    return _perform_transition(db, alert, "confirm", user)


def dismiss_alert(db: Session, alert_id: UUID, user: User, reason: str) -> Alert:
    alert = get_alert(db, alert_id)
    return _perform_transition(db, alert, "dismiss", user, reason=reason)


def resolve_alert(db: Session, alert_id: UUID, user: User) -> Alert:
    alert = get_alert(db, alert_id)
    return _perform_transition(db, alert, "resolve", user)
