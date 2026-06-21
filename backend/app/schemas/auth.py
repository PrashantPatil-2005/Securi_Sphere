from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    permissions: dict

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None = None
    role: RoleResponse
    is_active: bool
    created_at: datetime
    last_login: datetime | None

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
