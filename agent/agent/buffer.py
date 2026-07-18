import sqlite3
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("/var/lib/securi/buffer.db")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def enqueue(kind: str, payload: dict) -> None:
    import time
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO queue (kind, payload, created_at) VALUES (?, ?, ?)",
        (kind, json.dumps(payload), time.time()),
    )
    conn.commit()
    conn.close()


def dequeue_all() -> list[tuple[int, str, dict]]:
    """Return all items with their IDs so callers can remove only successful ones."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT id, kind, payload FROM queue ORDER BY id").fetchall()
    conn.close()
    return [(r[0], r[1], json.loads(r[2])) for r in rows]


def remove_by_ids(ids: list[int]) -> None:
    """Remove only the items that were successfully sent."""
    if not ids:
        return
    conn = sqlite3.connect(DB_PATH)
    placeholders = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM queue WHERE id IN ({placeholders})", ids)
    conn.commit()
    conn.close()


def queue_size() -> int:
    """Return number of items waiting in the offline buffer."""
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM queue").fetchone()[0]
    conn.close()
    return count


def clear_queue() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM queue")
    conn.commit()
    conn.close()


def purge_stale(max_age_hours: int = 48) -> int:
    """Remove items older than max_age_hours to prevent unbounded growth."""
    import time
    cutoff = time.time() - (max_age_hours * 3600)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("DELETE FROM queue WHERE created_at < ?", (cutoff,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    if deleted > 0:
        logger.warning("Purged %d stale items from offline buffer", deleted)
    return deleted
