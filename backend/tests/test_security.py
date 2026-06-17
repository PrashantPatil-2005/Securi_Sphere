import pytest
from app.security import hash_password, verify_password, hash_token, generate_api_key


def test_password_hashing():
    hashed = hash_password("testpassword123")
    assert verify_password("testpassword123", hashed)
    assert not verify_password("wrongpassword", hashed)


def test_token_hashing():
    token = "test-token-value"
    assert hash_token(token) == hash_token(token)
    assert len(hash_token(token)) == 64


def test_api_key_format():
    key = generate_api_key()
    assert key.startswith("sk_live_")
