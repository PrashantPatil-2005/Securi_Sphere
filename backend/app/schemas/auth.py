from datetime import datetime
import re
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.validators import AuthEmail

_PASSWORD_COMPLEXITY = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).{8,}$"
)


def _validate_password(v: str) -> str:
    if not _PASSWORD_COMPLEXITY.match(v):
        raise ValueError(
            "Password must be at least 8 characters and include uppercase, "
            "lowercase, digit, and special character"
        )
    return v


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
    mfa_enabled: bool = False
    created_at: datetime
    last_login: datetime | None

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    email: AuthEmail
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password(v)


class LoginRequest(BaseModel):
    email: AuthEmail
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    mfa_required: bool = False
    mfa_token: str | None = None


class MfaVerifyRequest(BaseModel):
    mfa_token: str
    code: str = Field(min_length=6, max_length=16)


class MfaEnableRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class MfaDisableRequest(BaseModel):
    code: str = Field(min_length=6, max_length=16)
    password: str | None = None


class MfaSetupResponse(BaseModel):
    secret: str
    otpauth_url: str


class MfaStatusResponse(BaseModel):
    enabled: bool
    backup_codes_remaining: int


class MfaEnableResponse(BaseModel):
    enabled: bool
    backup_codes: list[str]


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: AuthEmail


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password(v)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password(v)
