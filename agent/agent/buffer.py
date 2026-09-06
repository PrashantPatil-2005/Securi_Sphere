import sqlite3
import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("/var/lib/securi/buffer.db")

MAX_BUFFER_ITEMS = 50000
MAX_BUFFER_SIZE_MB = 200
SQLITE_BUSY_TIMEOUT_MS = 5000
MAX_EVENT_SIZE_BYTES = 4096
MAX_DEQUEUE_ITEMS = 200
STALE_ITEM_MAX_AGE_HOURS = 24


def _agent_rss_mb() -> float:
    try:
        with open("/proc/self/statm") as f:
            pages = int(f.read().split()[0])
        return pages * os.sysconf("SC_PAGE_SIZE") / (1024 * 1024)
    except Exception:
        return 0.0


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_queue_created_at ON queue(created_at)")
    conn.commit()
    conn.close()


def queue_size() -> int:
    conn = _connect()
    count = conn.execute("SELECT COUNT(*) FROM queue").fetchone()[0]
    conn.close()
    return count


def _buffer_size_mb() -> float:
    if not DB_PATH.exists():
        return 0.0
    return DB_PATH.stat().st_size / (1024 * 1024)


def _purge_oldest(conn: sqlite3.Connection, count: int) -> int:
    cursor = conn.execute(
        "DELETE FROM queue WHERE id IN (SELECT id FROM queue ORDER BY created_at ASC LIMIT ?)",
        (count,),
    )
    deleted = cursor.rowcount
    conn.commit()
    return deleted


def _purge_batch_wrappers(conn: sqlite3.Connection) -> int:
    """Remove legacy batch-wrapper rows left over from old agent versions.

    Old versions stored {"events": [...]} dicts. New version stores
    individual event dicts. Detect batch wrappers by the presence of
    an "events" key at the top level of the JSON payload.
    """
    cursor = conn.execute("SELECT id, payload FROM queue")
    ids_to_delete: list[int] = []
    for row_id, payload_json in cursor:
        try:
            payload = json.loads(payload_json)
            if isinstance(payload, dict) and "events" in payload and isinstance(payload["events"], list):
                ids_to_delete.append(row_id)
        except (json.JSONDecodeError, TypeError):
            pass
    cursor.close()
    if not ids_to_delete:
        return 0
    placeholders = ",".join("?" * len(ids_to_delete))
    conn.execute(f"DELETE FROM queue WHERE id IN ({placeholders})", ids_to_delete)
    conn.commit()
    logger.warning(
        "Purged %d legacy batch-wrapper rows from buffer (old agent format)",
        len(ids_to_delete),
    )
    return len(ids_to_delete)


def enqueue_event(event: dict, kind: str = "event") -> bool:
    """Buffer a single dict as one SQLite row.

    Each row is small (~300-2000 bytes). No nesting, no batch wrappers.
    kind is "event" or "metric".
    """
    payload_json = json.dumps(event, default=str)
    payload_bytes = len(payload_json.encode("utf-8"))
    if payload_bytes > MAX_EVENT_SIZE_BYTES:
        logger.warning(
            "Oversized event dropped: kind=event bytes=%d limit=%d type=%s",
            payload_bytes, MAX_EVENT_SIZE_BYTES,
            event.get("event_type", kind),
        )
        return False

    current_size = queue_size()
    current_mb = _buffer_size_mb()

    if current_size >= MAX_BUFFER_ITEMS:
        logger.warning("Buffer full (%d items) — dropping event", current_size)
        return False

    if current_mb >= MAX_BUFFER_SIZE_MB:
        logger.warning(
            "Buffer size exceeded (%.1f MB / %d MB) — purging oldest",
            current_mb, MAX_BUFFER_SIZE_MB,
        )
        conn = _connect()
        _purge_oldest(conn, MAX_BUFFER_ITEMS // 10)
        conn.close()

    try:
        conn = _connect()
        conn.execute(
            "INSERT INTO queue (kind, payload, created_at) VALUES (?, ?, ?)",
            (kind, payload_json, time.time()),
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.DataError as exc:
        logger.error(
            "SQLite rejected event write (%d bytes): %s — dropping",
            payload_bytes, exc,
        )
        return False


def enqueue_events(events: list[dict], kind: str = "event") -> int:
    """Buffer a list of individual items. Returns count successfully stored."""
    stored = 0
    for event in events:
        if enqueue_event(event, kind=kind):
            stored += 1
    return stored


def enqueue_metrics(metrics: list[dict]) -> int:
    return enqueue_events(metrics, kind="metric")


def dequeue_all(max_items: int = MAX_DEQUEUE_ITEMS) -> list[tuple[int, str, dict]]:
    """Return up to *max_items* individual event dicts.

    Each returned item is (id, "event", event_dict) — one event per row.
    Legacy batch-wrapper rows ({"events":[...]}) are transparently unwrapped
    into individual events and the old row is deleted.
    """
    conn = _connect()
    rows = conn.execute(
        "SELECT id, kind, payload FROM queue ORDER BY created_at ASC LIMIT ?",
        (max_items,),
    ).fetchall()
    conn.close()
    items: list[tuple[int, str, dict]] = []
    legacy_ids: list[int] = []
    for r in rows:
        try:
            parsed = json.loads(r[2])
            if isinstance(parsed, dict) and "events" in parsed and isinstance(parsed["events"], list):
                for evt in parsed["events"]:
                    if isinstance(evt, dict):
                        items.append((r[0], "event", evt))
                legacy_ids.append(r[0])
            else:
                items.append((r[0], r[1], parsed))
        except (json.JSONDecodeError, sqlite3.DataError) as exc:
            logger.warning("Dropping corrupt buffer item %d: %s", r[0], exc)
            remove_by_ids([r[0]])
    if legacy_ids:
        remove_by_ids(legacy_ids)
        logger.warning(
            "Purged %d legacy batch-wrapper rows (unwrapped to individual events)",
            len(legacy_ids),
        )
    return items


def remove_by_ids(ids: list[int]) -> None:
    if not ids:
        return
    conn = _connect()
    placeholders = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM queue WHERE id IN ({placeholders})", ids)
    conn.commit()
    conn.close()


def clear_queue() -> None:
    conn = _connect()
    conn.execute("DELETE FROM queue")
    conn.commit()
    conn.close()


def purge_stale(max_age_hours: int = 24) -> int:
    cutoff = time.time() - (max_age_hours * 3600)
    conn = _connect()
    cursor = conn.execute("DELETE FROM queue WHERE created_at < ?", (cutoff,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    if deleted > 0:
        logger.warning("Purged %d stale items from offline buffer", deleted)
    return deleted
