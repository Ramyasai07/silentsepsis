import uuid
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.patient import Patient, PatientStatus
from app.models.patient_baseline import PatientBaseline
from app.models.prediction import Prediction
from app.models.ward import Ward
from app.schemas.patient import PatientBaselineCreate, PatientCreate, PatientUpdate
from app.services.ward_service import ACTIVE_PATIENT_STATUSES


class PatientServiceError(Exception):
    message = "Patient service error"


class WardCapacityExceededError(PatientServiceError):
    message = "Ward capacity exceeded"


class DuplicateBedNumberError(PatientServiceError):
    message = "Bed number is already assigned in this ward"


class PatientNotFoundError(PatientServiceError):
    message = "Patient not found"


class WardNotFoundError(PatientServiceError):
    message = "Ward not found"


class BaselineNotFoundError(PatientServiceError):
    message = "Patient baseline not found"


def create_patient(db: Session, payload: PatientCreate) -> Patient:
    ward = _get_ward(db, payload.ward_id)
    _validate_ward_capacity(db, ward.id, ward.capacity)
    _validate_bed_available(db, ward.id, payload.bed_number)

    patient = Patient(
        hospital_patient_id=f"PAT-{uuid.uuid4().hex[:12].upper()}",
        full_name=payload.name,
        age=payload.age,
        gender=payload.sex,
        ward_id=ward.id,
        ward=ward,
        bed_number=payload.bed_number,
        admission_date=payload.admission_date,
        diagnosis=payload.admission_reason,
        current_status=PatientStatus.ADMITTED,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def get_patients(
    db: Session,
    *,
    ward_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, object]]:
    query = (
        select(Patient).options(joinedload(Patient.ward)).order_by(Patient.created_at)
    )
    if ward_id is not None:
        _get_ward(db, ward_id)
        query = query.where(Patient.ward_id == ward_id)

    patients = list(db.scalars(query.limit(limit).offset(offset)).all())
    return [to_patient_list_item(db, patient) for patient in patients]


def get_patient(db: Session, patient_id: UUID) -> Patient:
    patient = db.scalar(
        select(Patient)
        .options(joinedload(Patient.ward))
        .where(Patient.id == patient_id)
    )
    if patient is None:
        raise PatientNotFoundError()
    return patient


def update_patient(db: Session, patient_id: UUID, payload: PatientUpdate) -> Patient:
    patient = get_patient(db, patient_id)
    target_ward_id = payload.ward_id or patient.ward_id
    target_bed_number = payload.bed_number or patient.bed_number
    target_status = payload.discharge_status or patient.current_status

    if payload.ward_id is not None:
        ward = _get_ward(db, payload.ward_id)
    else:
        ward = patient.ward

    if _is_active_status(target_status):
        if payload.ward_id is not None and payload.ward_id != patient.ward_id:
            _validate_ward_capacity(
                db, ward.id, ward.capacity, exclude_patient_id=patient.id
            )
        _validate_bed_available(
            db,
            target_ward_id,
            target_bed_number,
            exclude_patient_id=patient.id,
        )

    patient.ward_id = target_ward_id
    patient.ward = ward
    patient.bed_number = target_bed_number
    if payload.discharge_date is not None:
        patient.discharge_date = payload.discharge_date
    if payload.discharge_status is not None:
        patient.current_status = payload.discharge_status

    db.commit()
    db.refresh(patient)
    return patient


def set_patient_baseline(
    db: Session,
    patient_id: UUID,
    payload: PatientBaselineCreate,
) -> PatientBaseline:
    patient = get_patient(db, patient_id)
    baseline = patient.baseline
    if baseline is None:
        baseline = PatientBaseline(patient_id=patient.id)
        db.add(baseline)

    baseline.baseline_hr = payload.baseline_hr
    baseline.baseline_spo2 = payload.baseline_spo2
    baseline.baseline_temperature = payload.baseline_temperature
    baseline.baseline_rr = payload.baseline_rr
    baseline.baseline_systolic_bp = payload.baseline_systolic_bp
    baseline.baseline_diastolic_bp = payload.baseline_diastolic_bp
    baseline.calculated_from_hours = payload.calculated_from_hours

    db.commit()
    db.refresh(baseline)
    return baseline


def get_patient_baseline(db: Session, patient_id: UUID) -> PatientBaseline:
    get_patient(db, patient_id)
    baseline = db.scalar(
        select(PatientBaseline).where(PatientBaseline.patient_id == patient_id)
    )
    if baseline is None:
        raise BaselineNotFoundError()
    return baseline


def to_patient_out(patient: Patient) -> dict[str, object]:
    return {
        "id": patient.id,
        "name": patient.full_name,
        "age": patient.age,
        "sex": patient.gender,
        "ward": {
            "id": patient.ward.id,
            "name": patient.ward.ward_name,
            "capacity": patient.ward.capacity,
        },
        "bed_number": patient.bed_number,
        "admission_date": patient.admission_date,
        "discharge_date": patient.discharge_date,
        "discharge_status": patient.current_status,
        "created_at": patient.created_at,
    }


def to_patient_list_item(db: Session, patient: Patient) -> dict[str, object]:
    return {
        "id": patient.id,
        "name": patient.full_name,
        "ward_name": patient.ward.ward_name,
        "bed_number": patient.bed_number,
        "risk_tier": _latest_risk_tier(db, patient.id),
        "current_status": patient.current_status,
    }


def _get_ward(db: Session, ward_id: UUID) -> Ward:
    ward = db.get(Ward, ward_id)
    if ward is None:
        raise WardNotFoundError()
    return ward


def _validate_ward_capacity(
    db: Session,
    ward_id: UUID,
    capacity: int,
    *,
    exclude_patient_id: UUID | None = None,
) -> None:
    query = (
        select(func.count())
        .select_from(Patient)
        .where(
            Patient.ward_id == ward_id,
            Patient.current_status.in_(ACTIVE_PATIENT_STATUSES),
        )
    )
    if exclude_patient_id is not None:
        query = query.where(Patient.id != exclude_patient_id)

    occupied = db.scalar(query) or 0
    if occupied >= capacity:
        raise WardCapacityExceededError()


def _validate_bed_available(
    db: Session,
    ward_id: UUID,
    bed_number: str,
    *,
    exclude_patient_id: UUID | None = None,
) -> None:
    query = select(Patient.id).where(
        Patient.ward_id == ward_id,
        Patient.bed_number == bed_number,
        Patient.current_status.in_(ACTIVE_PATIENT_STATUSES),
    )
    if exclude_patient_id is not None:
        query = query.where(Patient.id != exclude_patient_id)

    if db.scalar(query) is not None:
        raise DuplicateBedNumberError()


def _is_active_status(status: PatientStatus) -> bool:
    return status in ACTIVE_PATIENT_STATUSES


def _latest_risk_tier(db: Session, patient_id: UUID) -> str | None:
    latest_prediction = db.scalar(
        select(Prediction)
        .where(Prediction.patient_id == patient_id)
        .order_by(Prediction.generated_at.desc())
        .limit(1)
    )
    if latest_prediction is None:
        return None
    return latest_prediction.risk_level.value
