from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    capacity: int = Field(ge=0)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class WardOut(BaseModel):
    id: UUID
    name: str
    capacity: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WardSummaryOut(BaseModel):
    id: UUID
    name: str
    capacity: int
    occupied_beds: int
    available_beds: int
    ward: str
    activeAlerts: int
    trendingUp: int
    stable: int
    avgConfirmMinutes: float
    riskLoad: int
    totalPatients: int

    model_config = ConfigDict(from_attributes=True)
