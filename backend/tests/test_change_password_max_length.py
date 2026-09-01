"""Regression test: change-password should reject overly long passwords
with a 422, not crash with a 500 (bcrypt's 72-byte limit)."""
import pytest
from app.schemas.auth import ChangePasswordRequest
from pydantic import ValidationError


def test_new_password_over_72_bytes_rejected():
    long_password = "Aa1!" + "x" * 100  # well over 72 bytes, still meets complexity rules

    with pytest.raises(ValidationError):
        ChangePasswordRequest(
            current_password="whatever",
            new_password=long_password,
        )


def test_new_password_at_72_bytes_accepted():
    # 72 chars, ASCII => 72 bytes, satisfies complexity regex
    password = "Aa1!" + "x" * 68
    assert len(password) == 72

    req = ChangePasswordRequest(
        current_password="whatever",
        new_password=password,
    )
    assert req.new_password == password