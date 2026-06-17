import sqlite3
import json
from pathlib import Path

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
    conn.execute("INSERT INTO queue (kind, payload, created_at) VALUES (?, ?, ?)", (kind, json.dumps(payload), time.time()))
    conn.commit()
    conn.close()


def dequeue_all() -> list[tuple[str, dict]]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT id, kind, payload FROM queue ORDER BY id").fetchall()
    conn.close()
    return [(r[1], json.loads(r[2])) for r in rows]


def clear_queue() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM queue")
    conn.commit()
    conn.close()
