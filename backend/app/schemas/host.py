from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.validators import InetStr


class HostCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class HostResponse(BaseModel):
    id: UUID
    name: str
    hostname: str | None
    ip_address: InetStr
    os_info: str | None
    status: str
    enrolled: bool = False
    last_seen: datetime | None
    created_at: datetime
    risk_score: int | None = None
    alert_count: int | None = None

    model_config = {"from_attributes": True}


class HostListResponse(BaseModel):
    items: list[HostResponse]
    total: int
    page: int
    page_size: int


class EnrollmentTokenResponse(BaseModel):
    token: str
    expires_at: datetime
    install_command: str
    host_id: UUID
    host_name: str
    mtls_note: str | None = None


class AgentCertRegister(BaseModel):
    cert_fingerprint: str = Field(min_length=40, max_length=64)
