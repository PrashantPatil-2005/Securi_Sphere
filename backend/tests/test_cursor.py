from datetime import datetime, timezone
from uuid import uuid4

from app.utils.cursor import decode_event_cursor, encode_event_cursor


def test_event_cursor_roundtrip():
    event_id = uuid4()
    ts = datetime(2026, 1, 15, 12, 30, tzinfo=timezone.utc)
    encoded = encode_event_cursor(timestamp=ts, event_id=event_id, severity_rank=3)
    decoded_ts, decoded_id, decoded_sev = decode_event_cursor(encoded)
    assert decoded_id == event_id
    assert decoded_ts == ts
    assert decoded_sev == 3


def test_event_cursor_without_severity():
    event_id = uuid4()
    ts = datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc)
    encoded = encode_event_cursor(timestamp=ts, event_id=event_id)
    decoded_ts, decoded_id, decoded_sev = decode_event_cursor(encoded)
    assert decoded_id == event_id
    assert decoded_ts == ts
    assert decoded_sev is None
