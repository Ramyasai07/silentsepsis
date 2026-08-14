from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.feedback import FeedbackType


class FeedbackCreate(BaseModel):
    feedback_type: FeedbackType
    comments: str | None = Field(default=None, max_length=1000)

    model_config = ConfigDict(extra="forbid")


class FeedbackOut(BaseModel):
    id: UUID
    alert_id: UUID
    clinician_id: UUID | None
    feedback_type: FeedbackType
    comments: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
