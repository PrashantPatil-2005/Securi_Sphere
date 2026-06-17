from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class HostCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class HostResponse(BaseModel):
    id: UUID
    name: str
    hostname: str | None
    ip_address: str | None
    os_info: str | None
    status: str
    last_seen: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EnrollmentTokenResponse(BaseModel):
    token: str
    expires_at: datetime
    install_command: str
