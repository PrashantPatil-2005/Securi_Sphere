import re
from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from pydantic import BeforeValidator

_LOCAL_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def normalize_auth_email(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("email must be a string")
    email = value.strip().lower()
    if not email:
        raise ValueError("email is required")
    # Pydantic EmailStr rejects reserved domains like .local used in dev/test fixtures.
    if email.endswith(".local") or email.endswith(".test"):
        if not _LOCAL_EMAIL_RE.match(email):
            raise ValueError("invalid email format")
        return email
    try:
        return validate_email(email, check_deliverability=False).normalized
    except EmailNotValidError as exc:
        raise ValueError(str(exc)) from exc


AuthEmail = Annotated[str, BeforeValidator(normalize_auth_email)]
