import sqlite3
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("/var/lib/securi/buffer.db")

MAX_BUFFER_ITEMS = 50000
MAX_BUFFER_SIZE_MB = 500
SQLITE_BUSY_TIMEOUT_MS = 5000


def _connect() -> sqlite3.Connection:
    """Open a connection with WAL mode and busy timeout configured."""
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


def enqueue(kind: str, payload: dict) -> bool:
    import time

    current_size = queue_size()
    current_mb = _buffer_size_mb()

    if current_size >= MAX_BUFFER_ITEMS:
        logger.warning(
            "Buffer full (%d items) — dropping newest event",
            current_size,
        )
        return False

    if current_mb >= MAX_BUFFER_SIZE_MB:
        logger.warning(
            "Buffer size exceeded (%.1f MB / %d MB limit) — purging oldest",
            current_mb,
            MAX_BUFFER_SIZE_MB,
        )
        conn = _connect()
        _purge_oldest(conn, MAX_BUFFER_ITEMS // 10)
        conn.close()

    conn = _connect()
    conn.execute(
        "INSERT INTO queue (kind, payload, created_at) VALUES (?, ?, ?)",
        (kind, json.dumps(payload), time.time()),
    )
    conn.commit()
    conn.close()
    return True


def dequeue_all() -> list[tuple[int, str, dict]]:
    """Return all items with their IDs so callers can remove only successful ones."""
    conn = _connect()
    rows = conn.execute("SELECT id, kind, payload FROM queue ORDER BY id").fetchall()
    conn.close()
    return [(r[0], r[1], json.loads(r[2])) for r in rows]


def remove_by_ids(ids: list[int]) -> None:
    """Remove only the items that were successfully sent."""
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


def purge_stale(max_age_hours: int = 48) -> int:
    """Remove items older than max_age_hours to prevent unbounded growth."""
    import time
    cutoff = time.time() - (max_age_hours * 3600)
    conn = _connect()
    cursor = conn.execute("DELETE FROM queue WHERE created_at < ?", (cutoff,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    if deleted > 0:
        logger.warning("Purged %d stale items from offline buffer", deleted)
    return deleted
