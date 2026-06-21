from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

ALLOWED_SEVERITIES = {"info", "low", "medium", "high", "critical"}
MAX_BATCH_SIZE = 100
MAX_STRING_LEN = 8192
MAX_FUTURE_SKEW_SECONDS = 300
MAX_PAST_DAYS = 30


class ValidationError(Exception):
    def __init__(self, message: str, field: str | None = None):
        self.message = message
        self.field = field
        super().__init__(message)


def validate_event_payload(
    event_type: str,
    severity: str,
    timestamp: datetime,
    description: str | None = None,
    raw_log: str | None = None,
    metadata: dict | None = None,
) -> None:
    if not event_type or len(event_type) > 100:
        raise ValidationError("event_type must be 1-100 characters", "event_type")
    if severity not in ALLOWED_SEVERITIES:
        raise ValidationError(f"severity must be one of {ALLOWED_SEVERITIES}", "severity")

    now = datetime.now(timezone.utc)
    ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
    if ts > now:
        skew = (ts - now).total_seconds()
        if skew > MAX_FUTURE_SKEW_SECONDS:
            raise ValidationError("timestamp too far in the future", "timestamp")
    if (now - ts).days > MAX_PAST_DAYS:
        raise ValidationError(f"timestamp older than {MAX_PAST_DAYS} days rejected", "timestamp")

    for field_name, value in (("description", description), ("raw_log", raw_log)):
        if value and len(value) > MAX_STRING_LEN:
            raise ValidationError(f"{field_name} exceeds max length", field_name)

    if metadata and len(str(metadata)) > MAX_STRING_LEN * 2:
        raise ValidationError("metadata too large", "metadata")


def validate_batch_size(count: int) -> None:
    if count < 1:
        raise ValidationError("batch must contain at least one event")
    if count > MAX_BATCH_SIZE:
        raise ValidationError(f"batch exceeds max size of {MAX_BATCH_SIZE}")
