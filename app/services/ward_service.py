from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.patient import Patient, PatientStatus
from app.models.ward import Ward
from app.schemas.ward import WardCreate
from app.services.analytics_service import get_ward_summary_metrics

ACTIVE_PATIENT_STATUSES = (PatientStatus.ADMITTED, PatientStatus.TRANSFERRED)


class WardServiceError(Exception):
    message = "Ward service error"


class WardNotFoundError(WardServiceError):
    message = "Ward not found"


def create_ward(db: Session, payload: WardCreate) -> Ward:
    ward = Ward(
        ward_name=payload.name,
        department="General",
        capacity=payload.capacity,
    )
    db.add(ward)
    db.commit()
    db.refresh(ward)
    return ward


def get_wards(db: Session) -> list[Ward]:
    return list(db.scalars(select(Ward).order_by(Ward.ward_name)).all())


def get_ward(db: Session, ward_id: UUID) -> Ward:
    ward = db.get(Ward, ward_id)
    if ward is None:
        raise WardNotFoundError()
    return ward


def get_summary(db: Session, ward_id: UUID) -> dict[str, object]:
    ward = get_ward(db, ward_id)
    occupied_beds = _count_active_patients(db, ward.id)
    base_summary = {
        "id": ward.id,
        "name": ward.ward_name,
        "capacity": ward.capacity,
        "occupied_beds": occupied_beds,
        "available_beds": max(ward.capacity - occupied_beds, 0),
    }
    analytics = get_ward_summary_metrics(db, ward_id)
    return {**base_summary, **analytics}


def to_ward_out(ward: Ward) -> dict[str, object]:
    return {
        "id": ward.id,
        "name": ward.ward_name,
        "capacity": ward.capacity,
        "created_at": ward.created_at,
    }


def _count_active_patients(db: Session, ward_id: UUID) -> int:
    count = db.scalar(
        select(func.count())
        .select_from(Patient)
        .where(
            Patient.ward_id == ward_id,
            Patient.current_status.in_(ACTIVE_PATIENT_STATUSES),
        )
    )
    return count or 0
