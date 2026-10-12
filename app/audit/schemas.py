"""Audit schemas for SecureRoom."""

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    result: str
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True
