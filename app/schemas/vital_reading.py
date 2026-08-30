from datetime import datetime, timedelta, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class VitalReadingCreate(BaseModel):
    """Request schema for a single vital reading in Celsius units."""

    heart_rate: int = Field(..., ge=20, le=300)
    respiratory_rate: int = Field(..., ge=4, le=60)
    systolic_bp: int = Field(..., ge=40, le=260)
    diastolic_bp: int = Field(..., ge=20, le=200)
    spo2: float = Field(..., ge=0, le=100)
    temperature: float = Field(
        ...,
        ge=25.0,
        le=45.0,
        description="Temperature in Celsius",
    )
    recorded_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_vital_reading(self) -> "VitalReadingCreate":
        if self.diastolic_bp >= self.systolic_bp:
            raise ValueError("diastolic_bp must be less than systolic_bp")

        if self.recorded_at is not None:
            recorded_at = self.recorded_at
            if recorded_at.tzinfo is None:
                recorded_at = recorded_at.astimezone().astimezone(timezone.utc)
            else:
                recorded_at = recorded_at.astimezone(timezone.utc)

            if recorded_at > datetime.now(timezone.utc) + timedelta(minutes=5):
                raise ValueError(
                    "recorded_at cannot be more than 5 minutes in the future"
                )

            self.recorded_at = recorded_at

        return self


class VitalReadingBatchCreate(BaseModel):
    patient_id: UUID
    readings: list[VitalReadingCreate] = Field(..., min_length=1, max_length=100)

    model_config = ConfigDict(extra="forbid")


class VitalReadingOut(BaseModel):
    id: UUID
    patient_id: UUID
    recorded_by: UUID | None
    heart_rate: int
    respiratory_rate: int
    systolic_bp: int
    diastolic_bp: int
    spo2: float
    temperature: float
    recorded_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

