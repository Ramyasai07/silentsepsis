from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PredictionCreate(BaseModel):
    patient_id: UUID
    vital_reading_id: UUID | None = None

    model_config = ConfigDict(extra="forbid")


class PredictionFeatureOut(BaseModel):
    feature_name: str
    contribution: float

    model_config = ConfigDict(from_attributes=True)


class PredictionOut(BaseModel):
    id: UUID
    patient_id: UUID
    vital_reading_id: UUID
    risk_score: float
    risk_tier: str
    created_at: datetime
    features: list[PredictionFeatureOut]

    model_config = ConfigDict(from_attributes=True)
