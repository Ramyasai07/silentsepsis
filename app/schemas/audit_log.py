from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    id: UUID
    user_id: UUID | None
    action: str
    entity: str
    entity_id: UUID | None
    ip_address: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
