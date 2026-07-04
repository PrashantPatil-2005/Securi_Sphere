"""Opaque keyset cursors for stable pagination."""

import base64
import json
from datetime import datetime, timezone
from uuid import UUID


def encode_event_cursor(*, timestamp: datetime, event_id: UUID, severity_rank: int | None = None) -> str:
    payload: dict[str, str | int] = {
        "t": timestamp.isoformat(),
        "i": str(event_id),
    }
    if severity_rank is not None:
        payload["s"] = severity_rank
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_event_cursor(cursor: str) -> tuple[datetime, UUID, int | None]:
    pad = "=" * (-len(cursor) % 4)
    data = json.loads(base64.urlsafe_b64decode(cursor + pad))
    ts = datetime.fromisoformat(data["t"])
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    severity_rank = data.get("s")
    return ts, UUID(data["i"]), int(severity_rank) if severity_rank is not None else None
