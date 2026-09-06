import json
import sqlite3
import threading
import time

import agent.buffer as buf


def test_init_db_creates_table(tmp_buffer_db):
    buf.init_db()
    conn = sqlite3.connect(tmp_buffer_db)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    conn.close()
    assert "queue" in tables


def test_enqueue_event_returns_true(tmp_buffer_db):
    buf.init_db()
    event = {"event_type": "test", "severity": "info", "raw_log": "hello"}
    assert buf.enqueue_event(event) is True


def test_enqueue_event_stores_individual_row(tmp_buffer_db):
    buf.init_db()
    event = {"event_type": "test", "severity": "info", "raw_log": "hello"}
    buf.enqueue_event(event)
    items = buf.dequeue_all()
    assert len(items) == 1
    item_id, kind, payload = items[0]
    assert kind == "event"
    assert payload["event_type"] == "test"


def test_enqueue_events_batch(tmp_buffer_db):
    buf.init_db()
    events = [{"event_type": f"type_{i}", "severity": "info", "raw_log": f"msg {i}"} for i in range(10)]
    stored = buf.enqueue_events(events)
    assert stored == 10
    assert buf.queue_size() == 10


def test_queue_size(tmp_buffer_db):
    buf.init_db()
    assert buf.queue_size() == 0
    buf.enqueue_event({"a": 1})
    buf.enqueue_event({"b": 2})
    assert buf.queue_size() == 2


def test_dequeue_all_returns_items(tmp_buffer_db):
    buf.init_db()
    buf.enqueue_event({"msg": "hello"})
    items = buf.dequeue_all()
    assert len(items) == 1
    item_id, kind, payload = items[0]
    assert isinstance(item_id, int)
    assert kind == "event"
    assert payload["msg"] == "hello"


def test_dequeue_all_ordering(tmp_buffer_db):
    buf.init_db()
    buf.enqueue_event({"seq": 1})
    buf.enqueue_event({"seq": 2})
    buf.enqueue_event({"seq": 3})
    items = buf.dequeue_all()
    assert [i[2]["seq"] for i in items] == [1, 2, 3]


def test_remove_by_ids(tmp_buffer_db):
    buf.init_db()
    buf.enqueue_event({"a": 1})
    buf.enqueue_event({"b": 2})
    items = buf.dequeue_all()
    buf.remove_by_ids([items[0][0]])
    remaining = buf.dequeue_all()
    assert len(remaining) == 1
    assert remaining[0][2]["b"] == 2


def test_clear_queue(tmp_buffer_db):
    buf.init_db()
    buf.enqueue_event({"x": 1})
    buf.enqueue_event({"y": 2})
    buf.clear_queue()
    assert buf.queue_size() == 0


def test_purge_stale(tmp_buffer_db):
    buf.init_db()
    buf.enqueue_event({"fresh": True})
    conn = sqlite3.connect(tmp_buffer_db)
    old_time = time.time() - 200 * 3600
    conn.execute("UPDATE queue SET created_at = ?", (old_time,))
    conn.commit()
    conn.close()
    buf.enqueue_event({"also_old": True})
    conn = sqlite3.connect(tmp_buffer_db)
    conn.execute("UPDATE queue SET created_at = ?", (old_time,))
    conn.commit()
    conn.close()
    buf.enqueue_event({"fresh2": True})
    deleted = buf.purge_stale(max_age_hours=48)
    assert deleted == 2
    remaining = buf.dequeue_all()
    assert len(remaining) == 1


def test_max_buffer_items(tmp_buffer_db):
    buf.init_db()
    original = buf.MAX_BUFFER_ITEMS
    buf.MAX_BUFFER_ITEMS = 3
    try:
        assert buf.enqueue_event({"n": 1}) is True
        assert buf.enqueue_event({"n": 2}) is True
        assert buf.enqueue_event({"n": 3}) is True
        assert buf.enqueue_event({"n": 4}) is False
    finally:
        buf.MAX_BUFFER_ITEMS = original


def test_concurrent_enqueue(tmp_buffer_db):
    buf.init_db()
    errors = []

    def worker(n):
        try:
            buf.enqueue_event({"thread": n})
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert buf.queue_size() == 20


def test_concurrent_flush_and_enqueue(tmp_buffer_db):
    buf.init_db()
    for i in range(10):
        buf.enqueue_event({"n": i})
    errors = []

    def flusher():
        try:
            buf.dequeue_all()
        except Exception as e:
            errors.append(e)

    def enqueuer():
        try:
            for i in range(10, 20):
                buf.enqueue_event({"n": i})
        except Exception as e:
            errors.append(e)

    t1 = threading.Thread(target=flusher)
    t2 = threading.Thread(target=enqueuer)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert errors == []


def test_event_size_limit(tmp_buffer_db):
    buf.init_db()
    original = buf.MAX_EVENT_SIZE_BYTES
    buf.MAX_EVENT_SIZE_BYTES = 100
    try:
        small = {"data": "x" * 50}
        assert buf.enqueue_event(small) is True
        large = {"data": "x" * 200}
        assert buf.enqueue_event(large) is False
        assert buf.queue_size() == 1
    finally:
        buf.MAX_EVENT_SIZE_BYTES = original


def test_purge_stale_returns_zero_when_nothing_old(tmp_buffer_db):
    buf.init_db()
    buf.enqueue_event({"fresh": True})
    deleted = buf.purge_stale(max_age_hours=48)
    assert deleted == 0
    assert buf.queue_size() == 1


def test_remove_by_ids_empty_list(tmp_buffer_db):
    buf.init_db()
    buf.enqueue_event({"a": 1})
    buf.remove_by_ids([])
    assert buf.queue_size() == 1


def test_oversized_event_is_dropped(tmp_buffer_db):
    """An event exceeding MAX_EVENT_SIZE_BYTES must be dropped, never stored."""
    buf.init_db()
    huge = {"raw_log": "x" * (buf.MAX_EVENT_SIZE_BYTES + 1000)}
    assert buf.enqueue_event(huge) is False
    assert buf.queue_size() == 0


def test_normal_events_buffer_and_dequeue(tmp_buffer_db):
    """Reproduce the exact flow: 50 normal events -> buffer -> dequeue -> send."""
    buf.init_db()
    events = [
        {
            "event_type": "ssh_login_success",
            "severity": "low",
            "description": "SSH login success for user",
            "source": "auth.log",
            "raw_log": "Sep 6 10:23:45 kali sshd[1234]: Accepted password for user from 192.168.1.1 port 22 ssh2",
            "timestamp": "2026-09-06T10:23:45Z",
        }
        for _ in range(50)
    ]

    stored = buf.enqueue_events(events)
    assert stored == 50
    assert buf.queue_size() == 50

    items = buf.dequeue_all()
    assert len(items) == 50
    for item_id, kind, payload in items:
        assert kind == "event"
        assert "event_type" in payload
        payload_json = json.dumps(payload, default=str)
        assert len(payload_json.encode("utf-8")) <= buf.MAX_EVENT_SIZE_BYTES


def test_legacy_batch_wrapper_is_unwrapped(tmp_buffer_db):
    """Legacy rows from old agent versions ({"events":[...]}) must be
    transparently unwrapped into individual events and the old row deleted."""
    buf.init_db()
    conn = sqlite3.connect(tmp_buffer_db)
    legacy_batch = {
        "events": [
            {"event_type": "old_event", "severity": "info", "raw_log": f"line {i}"}
            for i in range(5)
        ]
    }
    conn.execute(
        "INSERT INTO queue (kind, payload, created_at) VALUES (?, ?, ?)",
        ("events", json.dumps(legacy_batch), time.time()),
    )
    conn.commit()
    conn.close()

    assert buf.queue_size() == 1

    items = buf.dequeue_all()
    assert len(items) == 5
    for item_id, kind, payload in items:
        assert kind == "event"
        assert "event_type" in payload

    assert buf.queue_size() == 0


def test_no_batch_wrapper_crash(tmp_buffer_db):
    """The old crash: enqueue({"events": [50 events]}) -> json.dumps -> SQLite DataError.

    With the new design, batch wrappers are NEVER created. Each event is
    a separate row. This test verifies no batch wrapper is ever stored."""
    buf.init_db()
    events = [{"event_type": f"t{i}", "raw_log": "x" * 100} for i in range(50)]
    buf.enqueue_events(events)

    conn = sqlite3.connect(tmp_buffer_db)
    rows = conn.execute("SELECT payload FROM queue").fetchall()
    conn.close()

    for (payload_json,) in rows:
        payload = json.loads(payload_json)
        assert not (isinstance(payload, dict) and "events" in payload), (
            "Batch wrapper found in buffer — this causes the 'string or blob too big' crash"
        )
        assert isinstance(payload, dict) and "event_type" in payload


def test_memory_bounded_flush(tmp_buffer_db):
    """200 events buffered -> dequeue_all(MAX_DEQUEUE_ITEMS=200) -> all fit in memory
    as individual event dicts, no batch nesting."""
    buf.init_db()
    original = buf.MAX_DEQUEUE_ITEMS
    buf.MAX_DEQUEUE_ITEMS = 200
    try:
        for i in range(200):
            buf.enqueue_event({
                "event_type": "service_start",
                "severity": "info",
                "description": f"Service started: svc_{i}.service",
                "source": "syslog",
                "raw_log": f"Sep 6 10:00:00 kali systemd[1]: Started Service {i}.",
                "timestamp": "2026-09-06T10:00:00Z",
            })

        items = buf.dequeue_all()
        assert len(items) == 200

        events = [payload for _, _, payload in items]
        total_json_size = sum(len(json.dumps(e, default=str).encode()) for e in events)
        assert total_json_size < 500_000
    finally:
        buf.MAX_DEQUEUE_ITEMS = original


def test_enqueue_metrics_uses_metric_kind(tmp_buffer_db):
    buf.init_db()
    stored = buf.enqueue_metrics([
        {"cpu_percent": 1.0, "memory_percent": 2.0, "recorded_at": "2026-09-06T00:00:00Z"}
    ])
    assert stored == 1
    items = buf.dequeue_all()
    assert len(items) == 1
    assert items[0][1] == "metric"
    assert "cpu_percent" in items[0][2]
