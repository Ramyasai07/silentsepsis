from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy import func, select, case
from sqlalchemy.orm import Session
from app.models.alert import Alert, AlertStatus
from app.models.feedback import Feedback, FeedbackType
from app.models.prediction import Prediction, RiskLevel
from app.models.patient import Patient
from app.models.ward import Ward


class WardNotFoundError(Exception):
    message = "Ward not found"


def get_precision_recall_history(db: Session, days: int = 30, bucket_size_days: int = 5) -> list[dict[str, str | int | None]]:
    """
    Calculate precision/recall history using feedback data.
    THIS IS A FEEDBACK-DERIVED APPROXIMATION, NOT GROUND-TRUTH LABELS. Metrics are only as accurate as the clinician feedback provided.
    Precision = (CONFIRMED) / (CONFIRMED + FALSE_POSITIVE)
    Recall = (CONFIRMED) / (CONFIRMED + MISSED_CASE)
    Buckets with insufficient data return null for precision/recall to avoid division by zero.
    Bucket labels use incremental start day ("Day 1", "Day 6", etc.) for consistency.
    """
    if days <= 0 or bucket_size_days <= 0:
        raise ValueError("days and bucket_size_days must be positive integers")

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    buckets = []
    bucket_start = start_date
    bucket_num = 0
    while bucket_start < end_date:
        bucket_end = min(bucket_start + timedelta(days=bucket_size_days), end_date)
        buckets.append((bucket_start, bucket_end, f"Day {bucket_num * bucket_size_days + 1}"))
        bucket_start = bucket_end
        bucket_num += 1

    results = []
    for bucket_start, bucket_end, bucket_label in buckets:
        stmt = select(
            func.count(case((Feedback.feedback_type == FeedbackType.CONFIRMED, 1), else_=None)).label("true_positives"),
            func.count(case((Feedback.feedback_type == FeedbackType.FALSE_POSITIVE, 1), else_=None)).label("false_positives"),
            func.count(case((Feedback.feedback_type == FeedbackType.MISSED_CASE, 1), else_=None)).label("false_negatives")
        ).where(
            Feedback.created_at >= bucket_start,
            Feedback.created_at < bucket_end
        )

        row = db.execute(stmt).first()
        tp = row.true_positives or 0
        fp = row.false_positives or 0
        fn = row.false_negatives or 0

        precision = None
        if (tp + fp) > 0:
            precision = round((tp / (tp + fp)) * 100)

        recall = None
        if (tp + fn) > 0:
            recall = round((tp / (tp + fn)) * 100)

        results.append({
            "day": bucket_label,
            "precision": precision,
            "recall": recall
        })

    return results


def get_ward_summary_metrics(db: Session, ward_id: UUID, days: int = 30) -> dict[str, object]:
    """
    Calculate extended ward summary metrics for the existing Commit 4 endpoint.
    Analytics-layer-only mapping per explicit instructions:
    stable = RiskLevel.LOW (matches frontend "stable" field)
    trendingUp = RiskLevel.MODERATE (matches frontend "trendingUp" field)
    Uses actual verified Alert/Prediction model fields.
    """
    ward = db.get(Ward, ward_id)
    if not ward:
        raise WardNotFoundError()

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    active_statuses = [AlertStatus.ACTIVE.value, AlertStatus.WATCHING.value, AlertStatus.CONFIRMED.value]
    active_alerts_stmt = select(func.count()).select_from(Alert).join(Alert.patient).where(
        Patient.ward_id == ward_id,
        Alert.created_at >= start_date,
        Alert.created_at < end_date,
        Alert._status.in_(active_statuses)
    )
    active_alerts = db.scalar(active_alerts_stmt) or 0

    latest_preds_subquery = select(
        Prediction.patient_id,
        func.max(Prediction.generated_at).label("latest_generated_at")
    ).join(Prediction.patient).where(
        Patient.ward_id == ward_id
    ).group_by(Prediction.patient_id).subquery()

    stable_stmt = select(func.count()).select_from(Prediction).join(
        latest_preds_subquery,
        (Prediction.patient_id == latest_preds_subquery.c.patient_id) &
        (Prediction.generated_at == latest_preds_subquery.c.latest_generated_at)
    ).where(Prediction.risk_level == RiskLevel.LOW)
    stable = db.scalar(stable_stmt) or 0

    trendingup_stmt = select(func.count()).select_from(Prediction).join(
        latest_preds_subquery,
        (Prediction.patient_id == latest_preds_subquery.c.patient_id) &
        (Prediction.generated_at == latest_preds_subquery.c.latest_generated_at)
    ).where(Prediction.risk_level == RiskLevel.MODERATE)
    trendingup = db.scalar(trendingup_stmt) or 0

    avg_confirm_stmt = select(func.avg(func.extract('epoch', Alert.confirmed_at - Alert.created_at)/60)).select_from(Alert).join(Alert.patient).where(
        Patient.ward_id == ward_id,
        Alert.confirmed_at.isnot(None),
        Alert.created_at >= start_date
    )
    avg_confirm_minutes = db.scalar(avg_confirm_stmt) or 0.0

    riskload_stmt = select(func.avg(Prediction.risk_probability)).select_from(Prediction).join(
        latest_preds_subquery,
        (Prediction.patient_id == latest_preds_subquery.c.patient_id) &
        (Prediction.generated_at == latest_preds_subquery.c.latest_generated_at)
    )
    riskload = round((db.scalar(riskload_stmt) or 0.0) * 100)

    total_patients_stmt = select(func.count()).select_from(Patient).where(Patient.ward_id == ward_id)
    total_patients = db.scalar(total_patients_stmt) or 0

    return {
        "ward": ward.ward_name,
        "activeAlerts": active_alerts,
        "trendingUp": trendingup,
        "stable": stable,
        "avgConfirmMinutes": round(avg_confirm_minutes, 1),
        "riskLoad": riskload,
        "totalPatients": total_patients
    }


def get_staff_response_by_ward(db: Session, days: int = 30) -> list[dict[str, str | int]]:
    """
    Calculate staff response rate by ward.
    Reviewed status = any status other than the initial ACTIVE state (verified AlertStatus values).
    Returns whole-number percentages, 0 if ward has no alerts in the window.
    """
    if days <= 0:
        raise ValueError("days must be a positive integer")

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    wards = db.scalars(select(Ward)).all()
    results = []

    for ward in wards:
        total_alerts_stmt = select(func.count()).select_from(Alert).join(Alert.patient).where(
            Patient.ward_id == ward.id,
            Alert.created_at >= start_date,
            Alert.created_at < end_date
        )
        total_alerts = db.scalar(total_alerts_stmt) or 0

        if total_alerts == 0:
            results.append({"ward": ward.ward_name, "reviewed": 0})
            continue

        reviewed_stmt = select(func.count()).select_from(Alert).join(Alert.patient).where(
            Patient.ward_id == ward.id,
            Alert.created_at >= start_date,
            Alert.created_at < end_date,
            Alert._status != AlertStatus.ACTIVE.value
        )
        reviewed = db.scalar(reviewed_stmt) or 0

        response_rate = round((reviewed / total_alerts) * 100)
        results.append({"ward": ward.ward_name, "reviewed": response_rate})

    return results
