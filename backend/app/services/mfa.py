"""TOTP MFA helpers."""

from __future__ import annotations

import secrets

import pyotp

from app.brand import PRODUCT_NAME
from app.security import hash_token


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def totp_provisioning_uri(secret: str, email: str, issuer: str = PRODUCT_NAME) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def verify_totp(secret: str, code: str, *, valid_window: int = 1) -> bool:
    cleaned = code.strip().replace(" ", "")
    if not cleaned.isdigit() or len(cleaned) != 6:
        return False
    return pyotp.TOTP(secret).verify(cleaned, valid_window=valid_window)


def generate_backup_codes(count: int = 8) -> list[str]:
    return [secrets.token_hex(4).upper() for _ in range(count)]


def hash_backup_codes(codes: list[str]) -> list[str]:
    return [hash_token(code) for code in codes]


def verify_backup_code(stored_hashes: list[str], code: str) -> tuple[bool, list[str]]:
    cleaned = code.strip().replace("-", "").upper()
    if not cleaned:
        return False, stored_hashes
    digest = hash_token(cleaned)
    if digest not in stored_hashes:
        return False, stored_hashes
    return True, [h for h in stored_hashes if h != digest]
