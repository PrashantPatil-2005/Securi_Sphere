"""Unit tests for OpenSearch at-scale helpers."""

from datetime import datetime, timezone

from app.search.bulk import build_bulk_actions, chunk_iterable
from app.search.index_names import events_index_for, events_index_for_iso


def test_events_index_for_monthly_rollover():
    ts = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    assert events_index_for(ts) == "securi-events-2026.07"


def test_events_index_for_iso_string():
    assert events_index_for_iso("2026-01-05T10:00:00+00:00") == "securi-events-2026.01"


def test_build_bulk_actions_pairs_index_and_source():
    actions = build_bulk_actions("securi-events-2026.07", [("id-1", {"id": "id-1", "event_type": "login"})])
    assert actions == [
        {"index": {"_index": "securi-events-2026.07", "_id": "id-1"}},
        {"id": "id-1", "event_type": "login"},
    ]


def test_chunk_iterable_splits_batches():
    chunks = list(chunk_iterable([1, 2, 3, 4, 5], 2))
    assert chunks == [[1, 2], [3, 4], [5]]
