"""Seed a small development-only SilentSepsis demo dataset.

This script is intentionally additive and idempotent. It creates clearly
synthetic ward, patient, baseline, and vital records when missing, then uses the
real PredictionService and TrainedRiskPredictor to generate predictions and
alerts. It refuses to run unless DATABASE_URL points at the local application
database named exactly ``silentsepsis``.
"""

# ruff: noqa: E402
from __future__ import annotations

import sys
from argparse import ArgumentParser, Namespace
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, selectinload

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.db.session import SessionLocal
from app.ml.trained_predictor import TrainedRiskPredictor
from app.models.alert import Alert
from app.models.patient import Gender, Patient
from app.models.prediction import Prediction
from app.models.user import User
from app.models.vital_reading import VitalReading
from app.models.ward import Ward
from app.schemas.patient import PatientBaselineCreate, PatientCreate
from app.schemas.vital_reading import VitalReadingBatchCreate, VitalReadingCreate
from app.schemas.ward import WardCreate
from app.services.patient_service import create_patient, set_patient_baseline
from app.services.prediction_service import PredictionService
from app.services.vital_service import record_vitals_batch
from app.services.ward_service import create_ward

DEMO_ADMIN_EMAIL = "ramya.sai@silentsepsis.local"
LEGACY_DEMO_PATIENT_PREFIX = "Demo Patient"


@dataclass(frozen=True)
class WardSeed:
    name: str
    capacity: int


@dataclass(frozen=True)
class BaselineSeed:
    heart_rate: float
    respiratory_rate: float
    systolic_bp: float
    diastolic_bp: float
    spo2: float
    temperature: float


@dataclass(frozen=True)
class VitalSeed:
    hours_ago: int
    heart_rate: int
    respiratory_rate: int
    systolic_bp: int
    diastolic_bp: int
    spo2: float
    temperature: float


@dataclass(frozen=True)
class PatientSeed:
    name: str
    age: int
    gender: Gender
    ward_name: str
    bed_number: str
    admission_days_ago: int
    admission_reason: str
    baseline: BaselineSeed
    vitals: tuple[VitalSeed, ...]


WARD_SEEDS: tuple[WardSeed, ...] = (
    WardSeed("Medical ICU", 10),
    WardSeed("Emergency / High Dependency", 12),
    WardSeed("General Medicine", 18),
)

PATIENT_SEEDS: tuple[PatientSeed, ...] = (
    PatientSeed(
        name="Sravani Reddy",
        age=42,
        gender=Gender.FEMALE,
        ward_name="General Medicine",
        bed_number="GM-101",
        admission_days_ago=2,
        admission_reason="Community-acquired pneumonia observation",
        baseline=BaselineSeed(
            heart_rate=65,
            respiratory_rate=12,
            systolic_bp=125,
            diastolic_bp=80,
            spo2=99,
            temperature=36.0,
        ),
        vitals=(
            VitalSeed(30, 64, 12, 126, 80, 99, 36.0),
            VitalSeed(20, 66, 12, 125, 80, 99, 36.0),
            VitalSeed(10, 65, 13, 124, 78, 99, 36.1),
            VitalSeed(2, 65, 12, 125, 80, 99, 36.0),
        ),
    ),
    PatientSeed(
        name="Karthik Varma",
        age=68,
        gender=Gender.MALE,
        ward_name="General Medicine",
        bed_number="GM-102",
        admission_days_ago=4,
        admission_reason="Urinary tract infection with dehydration",
        baseline=BaselineSeed(
            heart_rate=90,
            respiratory_rate=20,
            systolic_bp=115,
            diastolic_bp=65,
            spo2=95,
            temperature=37.0,
        ),
        vitals=(
            VitalSeed(28, 84, 18, 124, 72, 96, 36.9),
            VitalSeed(18, 86, 19, 120, 70, 96, 37.0),
            VitalSeed(8, 88, 20, 118, 68, 95, 37.0),
            VitalSeed(1, 90, 20, 115, 65, 95, 37.0),
        ),
    ),
    PatientSeed(
        name="Sai Teja Rao",
        age=75,
        gender=Gender.MALE,
        ward_name="Emergency / High Dependency",
        bed_number="HDU-201",
        admission_days_ago=1,
        admission_reason="Possible biliary sepsis under evaluation",
        baseline=BaselineSeed(
            heart_rate=88,
            respiratory_rate=18,
            systolic_bp=128,
            diastolic_bp=74,
            spo2=96,
            temperature=37.1,
        ),
        vitals=(
            VitalSeed(24, 104, 23, 116, 66, 94, 38.1),
            VitalSeed(14, 112, 25, 108, 62, 93, 38.5),
            VitalSeed(6, 120, 27, 100, 58, 92, 38.8),
            VitalSeed(1, 126, 29, 96, 54, 91, 39.0),
        ),
    ),
    PatientSeed(
        name="Lakshmi Priya",
        age=59,
        gender=Gender.FEMALE,
        ward_name="Medical ICU",
        bed_number="ICU-301",
        admission_days_ago=3,
        admission_reason="Post-operative intra-abdominal infection",
        baseline=BaselineSeed(
            heart_rate=82,
            respiratory_rate=17,
            systolic_bp=126,
            diastolic_bp=72,
            spo2=97,
            temperature=36.9,
        ),
        vitals=(
            VitalSeed(32, 112, 25, 104, 60, 93, 38.4),
            VitalSeed(18, 124, 29, 96, 56, 91, 38.9),
            VitalSeed(7, 136, 33, 88, 50, 89, 39.3),
            VitalSeed(1, 148, 36, 82, 46, 87, 39.7),
        ),
    ),
    PatientSeed(
        name="Vamsi Krishna",
        age=53,
        gender=Gender.MALE,
        ward_name="Medical ICU",
        bed_number="ICU-302",
        admission_days_ago=5,
        admission_reason="Severe soft tissue infection requiring monitoring",
        baseline=BaselineSeed(
            heart_rate=84,
            respiratory_rate=18,
            systolic_bp=124,
            diastolic_bp=76,
            spo2=97,
            temperature=36.8,
        ),
        vitals=(
            VitalSeed(36, 96, 21, 118, 70, 95, 37.6),
            VitalSeed(24, 104, 24, 110, 64, 93, 38.1),
            VitalSeed(12, 115, 27, 104, 60, 91, 38.6),
            VitalSeed(2, 128, 30, 98, 56, 90, 39.1),
        ),
    ),
    PatientSeed(
        name="Harika Reddy",
        age=34,
        gender=Gender.FEMALE,
        ward_name="Emergency / High Dependency",
        bed_number="HDU-202",
        admission_days_ago=1,
        admission_reason="Pyelonephritis with fever and tachycardia",
        baseline=BaselineSeed(
            heart_rate=96,
            respiratory_rate=21,
            systolic_bp=112,
            diastolic_bp=64,
            spo2=94,
            temperature=37.2,
        ),
        vitals=(
            VitalSeed(18, 88, 18, 116, 68, 96, 37.0),
            VitalSeed(10, 92, 20, 114, 66, 95, 37.1),
            VitalSeed(4, 94, 21, 112, 64, 95, 37.2),
            VitalSeed(1, 96, 21, 112, 64, 94, 37.2),
        ),
    ),
    PatientSeed(
        name="Nikhil Kumar",
        age=81,
        gender=Gender.MALE,
        ward_name="General Medicine",
        bed_number="GM-103",
        admission_days_ago=6,
        admission_reason="Chronic obstructive pulmonary disease exacerbation",
        baseline=BaselineSeed(
            heart_rate=70,
            respiratory_rate=14,
            systolic_bp=130,
            diastolic_bp=80,
            spo2=98,
            temperature=36.0,
        ),
        vitals=(
            VitalSeed(34, 68, 14, 132, 80, 98, 36.0),
            VitalSeed(22, 70, 14, 130, 80, 98, 36.0),
            VitalSeed(12, 72, 15, 128, 78, 97, 36.1),
            VitalSeed(3, 70, 14, 130, 80, 98, 36.0),
        ),
    ),
    PatientSeed(
        name="Anusha Devi",
        age=47,
        gender=Gender.FEMALE,
        ward_name="Emergency / High Dependency",
        bed_number="HDU-203",
        admission_days_ago=2,
        admission_reason="Cellulitis with systemic inflammatory response",
        baseline=BaselineSeed(
            heart_rate=80,
            respiratory_rate=16,
            systolic_bp=120,
            diastolic_bp=72,
            spo2=98,
            temperature=36.7,
        ),
        vitals=(
            VitalSeed(26, 92, 19, 116, 68, 97, 37.8),
            VitalSeed(16, 100, 22, 112, 64, 96, 38.2),
            VitalSeed(7, 110, 25, 106, 60, 94, 38.7),
            VitalSeed(1, 118, 27, 102, 58, 93, 39.0),
        ),
    ),
)

DEMO_PATIENT_NAMES = tuple(seed.name for seed in PATIENT_SEEDS)


def guard_database_url() -> None:
    url = make_url(settings.database_url)
    database = url.database or ""
    if database != "silentsepsis" or "test" in database.lower():
        raise RuntimeError(
            "Refusing to seed demo data: DATABASE_URL must point exactly to the "
            f"local application database 'silentsepsis' (got {database!r})."
        )


def find_or_create_ward(db: Session, seed: WardSeed) -> tuple[Ward, bool]:
    ward = db.scalar(select(Ward).where(Ward.ward_name == seed.name))
    if ward is not None:
        return ward, False
    return create_ward(db, WardCreate(name=seed.name, capacity=seed.capacity)), True


def find_or_create_patient(
    db: Session,
    seed: PatientSeed,
    ward: Ward,
    now: datetime,
) -> tuple[Patient, bool]:
    patient = db.scalar(select(Patient).where(Patient.full_name == seed.name))
    if patient is not None:
        return patient, False

    patient = db.scalar(
        select(Patient).where(
            Patient.ward_id == ward.id,
            Patient.bed_number == seed.bed_number,
            Patient.full_name.like(f"{LEGACY_DEMO_PATIENT_PREFIX}%"),
        )
    )
    if patient is not None:
        patient.full_name = seed.name
        patient.age = seed.age
        patient.gender = seed.gender
        patient.diagnosis = seed.admission_reason
        db.commit()
        db.refresh(patient)
        return patient, False

    patient = create_patient(
        db,
        PatientCreate(
            name=seed.name,
            age=seed.age,
            sex=seed.gender,
            ward_id=ward.id,
            bed_number=seed.bed_number,
            admission_date=now - timedelta(days=seed.admission_days_ago),
            admission_reason=seed.admission_reason,
        ),
    )
    return patient, True


def upsert_baseline(db: Session, patient: Patient, seed: BaselineSeed) -> None:
    set_patient_baseline(
        db,
        patient.id,
        PatientBaselineCreate(
            baseline_hr=seed.heart_rate,
            baseline_spo2=seed.spo2,
            baseline_temperature=seed.temperature,
            baseline_rr=seed.respiratory_rate,
            baseline_systolic_bp=seed.systolic_bp,
            baseline_diastolic_bp=seed.diastolic_bp,
            calculated_from_hours=24,
        ),
    )


def ensure_vitals(
    db: Session,
    patient: Patient,
    seed: PatientSeed,
    recorded_by: UUID | None,
    now: datetime,
) -> tuple[list[VitalReading], int]:
    existing = list(
        db.scalars(
            select(VitalReading)
            .where(VitalReading.patient_id == patient.id)
            .order_by(VitalReading.recorded_at)
        ).all()
    )
    if existing:
        return existing, 0

    payload = VitalReadingBatchCreate(
        patient_id=patient.id,
        readings=[
            VitalReadingCreate(
                heart_rate=item.heart_rate,
                respiratory_rate=item.respiratory_rate,
                systolic_bp=item.systolic_bp,
                diastolic_bp=item.diastolic_bp,
                spo2=item.spo2,
                temperature=item.temperature,
                recorded_at=now - timedelta(hours=item.hours_ago),
            )
            for item in seed.vitals
        ],
    )
    vitals = record_vitals_batch(db, patient.id, payload, recorded_by)
    return vitals, len(vitals)


def latest_vital(db: Session, patient_id: UUID) -> VitalReading:
    vital = db.scalar(
        select(VitalReading)
        .where(VitalReading.patient_id == patient_id)
        .order_by(VitalReading.recorded_at.desc())
        .limit(1)
    )
    if vital is None:
        raise RuntimeError(f"No vital readings found for patient {patient_id}")
    return vital


def ensure_prediction(
    db: Session,
    service: PredictionService,
    patient: Patient,
    vital: VitalReading,
) -> tuple[Prediction, bool]:
    prediction = db.scalar(
        select(Prediction)
        .where(
            Prediction.patient_id == patient.id,
            Prediction.vital_reading_id == vital.id,
        )
        .options(selectinload(Prediction.features))
        .order_by(Prediction.generated_at.desc())
        .limit(1)
    )
    if prediction is not None:
        return prediction, False

    prediction = service.generate_prediction(
        db,
        patient_id=patient.id,
        vital_reading_id=vital.id,
    )
    prediction = db.scalar(
        select(Prediction)
        .where(Prediction.id == prediction.id)
        .options(selectinload(Prediction.features))
    )
    if prediction is None:
        raise RuntimeError("Prediction was created but could not be reloaded")
    return prediction, True


def get_demo_recorder(db: Session) -> UUID | None:
    user = db.scalar(select(User).where(User.email == DEMO_ADMIN_EMAIL))
    return user.id if user is not None else None


def replace_demo_patients(db: Session) -> int:
    patients = list(
        db.scalars(
            select(Patient).where(
                (Patient.full_name.in_(DEMO_PATIENT_NAMES))
                | (Patient.full_name.like(f"{LEGACY_DEMO_PATIENT_PREFIX}%"))
            )
        ).all()
    )
    for patient in patients:
        db.delete(patient)
    db.commit()
    return len(patients)


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Seed synthetic local development demo data into silentsepsis."
    )
    parser.add_argument(
        "--replace-demo",
        action="store_true",
        help=(
            "Delete and recreate only the synthetic demo patients and their "
            "cascading vitals, predictions, and alerts before seeding."
        ),
    )
    return parser.parse_args()


def run() -> int:
    args = parse_args()
    guard_database_url()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    prediction_service = PredictionService(TrainedRiskPredictor())

    with SessionLocal() as db:
        replaced_patients = replace_demo_patients(db) if args.replace_demo else 0
        recorder_id = get_demo_recorder(db)
        wards_by_name: dict[str, Ward] = {}
        created_wards = 0
        created_patients = 0
        created_vitals = 0
        created_predictions = 0

        for ward_seed in WARD_SEEDS:
            ward, created = find_or_create_ward(db, ward_seed)
            wards_by_name[ward_seed.name] = ward
            created_wards += int(created)

        predictions: list[Prediction] = []
        for patient_seed in PATIENT_SEEDS:
            ward = wards_by_name[patient_seed.ward_name]
            patient, patient_created = find_or_create_patient(
                db,
                patient_seed,
                ward,
                now,
            )
            created_patients += int(patient_created)
            upsert_baseline(db, patient, patient_seed.baseline)
            _vitals, vital_count = ensure_vitals(
                db,
                patient,
                patient_seed,
                recorder_id,
                now,
            )
            created_vitals += vital_count
            vital = latest_vital(db, patient.id)
            prediction, prediction_created = ensure_prediction(
                db,
                prediction_service,
                patient,
                vital,
            )
            created_predictions += int(prediction_created)
            predictions.append(prediction)

        alert_count = db.scalar(
            select(func.count())
            .select_from(Alert)
            .join(Patient)
            .where(Patient.full_name.in_(DEMO_PATIENT_NAMES))
        )

        risk_distribution = Counter(prediction.risk_tier for prediction in predictions)

        print("SilentSepsis demo seed complete")
        print(f"Database: {make_url(settings.database_url).database}")
        print(f"Demo patients replaced: {replaced_patients}")
        print(f"Wards created: {created_wards}")
        print(f"Patients created: {created_patients}")
        print(f"Vitals created: {created_vitals}")
        print(f"Predictions created: {created_predictions}")
        print(f"Demo alerts present: {alert_count or 0}")
        print("Risk distribution:")
        for tier in ("LOW", "MODERATE", "HIGH", "CRITICAL"):
            print(f"  {tier}: {risk_distribution.get(tier, 0)}")
        print("Predictions:")
        for prediction in predictions:
            patient = db.get(Patient, prediction.patient_id)
            top_features = ", ".join(
                f"{feature.feature_name}={feature.contribution:.3f}"
                for feature in prediction.features[:3]
            )
            patient_name = (
                patient.full_name if patient is not None else prediction.patient_id
            )
            print(
                f"  {patient_name}: {prediction.risk_score:.4f} "
                f"{prediction.risk_tier} prediction={prediction.id} "
                f"vital={prediction.vital_reading_id} top=[{top_features}]"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
