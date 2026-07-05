"""JWT helpers — HS256 (dev) or RS256 (production)."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_private_key: str | None = None
_public_key: str | None = None


def jwt_algorithm() -> str:
    return settings.jwt_algorithm.upper()


def _load_rsa_keys() -> tuple[str, str]:
    global _private_key, _public_key
    if _private_key and _public_key:
        return _private_key, _public_key
    if not settings.jwt_private_key_path or not settings.jwt_public_key_path:
        raise ValueError("JWT_PRIVATE_KEY_PATH and JWT_PUBLIC_KEY_PATH required for RS256")
    _private_key = Path(settings.jwt_private_key_path).read_text(encoding="utf-8")
    _public_key = Path(settings.jwt_public_key_path).read_text(encoding="utf-8")
    return _private_key, _public_key


def _signing_key() -> str:
    if jwt_algorithm() == "RS256":
        return _load_rsa_keys()[0]
    return settings.jwt_secret


def _verify_key() -> str:
    if jwt_algorithm() == "RS256":
        return _load_rsa_keys()[1]
    return settings.jwt_secret


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_api_key() -> str:
    return f"sk_live_{secrets.token_urlsafe(32)}"


def generate_enrollment_token() -> str:
    return f"enroll_{secrets.token_urlsafe(32)}"


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


def _encode(payload: dict) -> str:
    return jwt.encode(payload, _signing_key(), algorithm=jwt_algorithm())


def create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_expire_minutes)
    return _encode({"sub": subject, "role": role, "type": "access", "exp": expire})


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)
    return _encode({"sub": subject, "type": "refresh", "exp": expire})


def create_ws_ticket(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(seconds=60)
    return _encode({"sub": subject, "type": "ws", "exp": expire})


def decode_token(token: str) -> dict:
    return jwt.decode(token, _verify_key(), algorithms=[jwt_algorithm()])


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()
