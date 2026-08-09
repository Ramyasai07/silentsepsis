from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AlertDismissRequest(BaseModel):
    reason: str = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid")


class AlertListItem(BaseModel):
    id: UUID
    patient_id: UUID
    prediction_id: UUID
    severity: str
    status: str
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertOut(BaseModel):
    id: UUID
    patient_id: UUID
    prediction_id: UUID
    severity: str
    status: str
    message: str
    acknowledged_at: datetime | None = None
    acknowledged_by: UUID | None = None
    confirmed_at: datetime | None = None
    confirmed_by: UUID | None = None
    dismissed_at: datetime | None = None
    dismissed_by: UUID | None = None
    dismissed_reason: str | None = None
    resolved_at: datetime | None = None
    resolved_by: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
