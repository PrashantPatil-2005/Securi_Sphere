import pyotp

from app.services.mfa import (
    generate_backup_codes,
    generate_totp_secret,
    hash_backup_codes,
    verify_backup_code,
    verify_totp,
)


def test_verify_totp_valid_code():
    secret = pyotp.random_base32()
    code = pyotp.TOTP(secret).now()
    assert verify_totp(secret, code)


def test_verify_totp_rejects_garbage():
    secret = generate_totp_secret()
    assert not verify_totp(secret, "abc")
    assert not verify_totp(secret, "12345")


def test_backup_code_single_use():
    codes = generate_backup_codes(2)
    hashes = hash_backup_codes(codes)
    ok, remaining = verify_backup_code(hashes, codes[0])
    assert ok
    assert len(remaining) == 1
    ok2, _ = verify_backup_code(remaining, codes[0])
    assert not ok2
