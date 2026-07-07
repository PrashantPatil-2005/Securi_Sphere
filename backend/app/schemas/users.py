from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.auth import RoleResponse
from app.schemas.validators import AuthEmail


class UserAdminResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    role: RoleResponse
    is_active: bool
    last_login: datetime | None
    sso_only: bool
    oidc_linked: bool

    model_config = {"from_attributes": True}


class UserProvisionRequest(BaseModel):
    email: AuthEmail
    role: str = Field(pattern="^(admin|analyst|viewer)$")
    full_name: str | None = Field(default=None, max_length=255)
    sso_only: bool = False
    password: str | None = Field(default=None, min_length=8)


class UserUpdateRequest(BaseModel):
    role: str | None = Field(default=None, pattern="^(admin|analyst|viewer)$")
    is_active: bool | None = None


class UserInviteCreateRequest(BaseModel):
    email: AuthEmail
    role: str = Field(pattern="^(admin|analyst|viewer)$")
    full_name: str | None = Field(default=None, max_length=255)


class UserInviteResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    role: str
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime
    invite_url: str | None = None


class InvitePreviewResponse(BaseModel):
    email: str
    full_name: str | None
    role: str
    expires_at: datetime


class InviteAcceptRequest(BaseModel):
    token: str = Field(min_length=16)
    password: str | None = Field(default=None, min_length=8)
    full_name: str | None = Field(default=None, max_length=255)
