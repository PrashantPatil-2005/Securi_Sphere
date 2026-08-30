import sqlite3
import threading
import time

import pytest

import agent.buffer as buf


def test_init_db_creates_table(tmp_buffer_db):
    buf.init_db()
    conn = sqlite3.connect(tmp_buffer_db)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    conn.close()
    assert "queue" in tables


def test_enqueue_returns_true(tmp_buffer_db):
    buf.init_db()
    assert buf.enqueue("events", {"e": 1}) is True


def test_queue_size(tmp_buffer_db):
    buf.init_db()
    assert buf.queue_size() == 0
    buf.enqueue("events", {"a": 1})
    buf.enqueue("metrics", {"b": 2})
    assert buf.queue_size() == 2


def test_dequeue_all_returns_items(tmp_buffer_db):
    buf.init_db()
    buf.enqueue("events", {"msg": "hello"})
    items = buf.dequeue_all()
    assert len(items) == 1
    item_id, kind, payload = items[0]
    assert isinstance(item_id, int)
    assert kind == "events"
    assert payload["msg"] == "hello"


def test_dequeue_all_ordering(tmp_buffer_db):
    buf.init_db()
    buf.enqueue("events", {"seq": 1})
    buf.enqueue("events", {"seq": 2})
    buf.enqueue("events", {"seq": 3})
    items = buf.dequeue_all()
    assert [i[2]["seq"] for i in items] == [1, 2, 3]


def test_remove_by_ids(tmp_buffer_db):
    buf.init_db()
    buf.enqueue("events", {"a": 1})
    buf.enqueue("events", {"b": 2})
    items = buf.dequeue_all()
    buf.remove_by_ids([items[0][0]])
    remaining = buf.dequeue_all()
    assert len(remaining) == 1
    assert remaining[0][2]["b"] == 2


def test_clear_queue(tmp_buffer_db):
    buf.init_db()
    buf.enqueue("events", {"x": 1})
    buf.enqueue("metrics", {"y": 2})
    buf.clear_queue()
    assert buf.queue_size() == 0


def test_purge_stale(tmp_buffer_db):
    buf.init_db()
    buf.enqueue("events", {"fresh": True})
    conn = sqlite3.connect(tmp_buffer_db)
    old_time = time.time() - 200 * 3600
    conn.execute("UPDATE queue SET created_at = ?", (old_time,))
    conn.commit()
    conn.close()
    buf.enqueue("events", {"also_old": True})
    conn = sqlite3.connect(tmp_buffer_db)
    conn.execute("UPDATE queue SET created_at = ?", (old_time,))
    conn.commit()
    conn.close()
    buf.enqueue("events", {"fresh2": True})
    deleted = buf.purge_stale(max_age_hours=48)
    assert deleted == 2
    remaining = buf.dequeue_all()
    assert len(remaining) == 1


def test_max_buffer_items(tmp_buffer_db):
    buf.init_db()
    original = buf.MAX_BUFFER_ITEMS
    buf.MAX_BUFFER_ITEMS = 3
    try:
        assert buf.enqueue("events", {"n": 1}) is True
        assert buf.enqueue("events", {"n": 2}) is True
        assert buf.enqueue("events", {"n": 3}) is True
        assert buf.enqueue("events", {"n": 4}) is False
    finally:
        buf.MAX_BUFFER_ITEMS = original


def test_concurrent_enqueue(tmp_buffer_db):
    buf.init_db()
    errors = []

    def worker(n):
        try:
            buf.enqueue("events", {"thread": n})
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
        buf.enqueue("events", {"n": i})
    errors = []

    def flusher():
        try:
            buf.dequeue_all()
        except Exception as e:
            errors.append(e)

    def enqueuer():
        try:
            for i in range(10, 20):
                buf.enqueue("events", {"n": i})
        except Exception as e:
            errors.append(e)

    t1 = threading.Thread(target=flusher)
    t2 = threading.Thread(target=enqueuer)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert errors == []
