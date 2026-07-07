"""PostgreSQL backup automation — pg_dump, retention, manifests."""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import json
import logging
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class BackupRecord:
    filename: str
    path: str
    size_bytes: int
    sha256: str
    created_at: str
    trigger: str
    duration_seconds: float
    database: str
    status: str = "completed"
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_pg_url(database_url: str) -> str:
    for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://", "postgresql+psycopg2://"):
        if database_url.startswith(prefix):
            return "postgresql://" + database_url[len(prefix) :]
    return database_url


def backup_directory() -> Path:
    path = Path(settings.backup_directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _manifest_path(archive: Path) -> Path:
    return archive.with_suffix("").with_suffix(".manifest.json")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_manifest(archive: Path, record: BackupRecord) -> None:
    manifest = _manifest_path(archive)
    manifest.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")


def _read_manifest(archive: Path) -> BackupRecord | None:
    manifest = _manifest_path(archive)
    if not manifest.exists():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return BackupRecord(**data)
    except (json.JSONDecodeError, TypeError):
        return None


def list_backups(limit: int = 50) -> list[BackupRecord]:
    directory = backup_directory()
    archives = sorted(directory.glob("securi_pg_*.sql.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    records: list[BackupRecord] = []
    for archive in archives[:limit]:
        record = _read_manifest(archive)
        if record is None:
            stat = archive.stat()
            record = BackupRecord(
                filename=archive.name,
                path=str(archive),
                size_bytes=stat.st_size,
                sha256="",
                created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                trigger="unknown",
                duration_seconds=0.0,
                database="securi",
                status="completed",
            )
        records.append(record)
    return records


def prune_old_backups(retention_days: int | None = None) -> list[str]:
    days = retention_days if retention_days is not None else settings.backup_retention_days
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    removed: list[str] = []
    directory = backup_directory()
    for archive in directory.glob("securi_pg_*.sql.gz"):
        created = datetime.fromtimestamp(archive.stat().st_mtime, tz=timezone.utc)
        if created < cutoff:
            manifest = _manifest_path(archive)
            archive.unlink(missing_ok=True)
            manifest.unlink(missing_ok=True)
            removed.append(archive.name)
    return removed


def _database_name(database_url: str) -> str:
    normalized = normalize_pg_url(database_url)
    return normalized.rsplit("/", 1)[-1].split("?")[0] or "securi"


def _run_pg_dump_sync(*, trigger: str) -> BackupRecord:
    if shutil.which("pg_dump") is None:
        raise RuntimeError("pg_dump not found — install postgresql-client on the backend host")

    started = datetime.now(timezone.utc)
    directory = backup_directory()
    stamp = started.strftime("%Y%m%d_%H%M%S")
    archive = directory / f"securi_pg_{stamp}.sql.gz"
    db_name = _database_name(settings.database_url)
    url = normalize_pg_url(settings.database_url)

    try:
        with gzip.open(archive, "wb") as gz:
            result = subprocess.run(
                ["pg_dump", "--no-owner", "--no-acl", url],
                check=False,
                stdout=gz,
                stderr=subprocess.PIPE,
            )
        if result.returncode != 0:
            archive.unlink(missing_ok=True)
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(stderr or f"pg_dump exited {result.returncode}")

        duration = (datetime.now(timezone.utc) - started).total_seconds()
        record = BackupRecord(
            filename=archive.name,
            path=str(archive),
            size_bytes=archive.stat().st_size,
            sha256=_sha256_file(archive),
            created_at=started.isoformat(),
            trigger=trigger,
            duration_seconds=round(duration, 2),
            database=db_name,
        )
        _write_manifest(archive, record)
        return record
    except Exception as exc:
        archive.unlink(missing_ok=True)
        failed = BackupRecord(
            filename=archive.name,
            path=str(archive),
            size_bytes=0,
            sha256="",
            created_at=started.isoformat(),
            trigger=trigger,
            duration_seconds=round((datetime.now(timezone.utc) - started).total_seconds(), 2),
            database=db_name,
            status="failed",
            error=str(exc),
        )
        raise RuntimeError(str(exc)) from exc


async def run_postgres_backup(*, trigger: str = "scheduled") -> BackupRecord:
    record = await asyncio.to_thread(_run_pg_dump_sync, trigger=trigger)
    removed = prune_old_backups()
    if removed:
        logger.info("Pruned %s old backup(s)", len(removed))
    logger.info(
        "Postgres backup completed",
        extra={"filename": record.filename, "bytes": record.size_bytes, "trigger": trigger},
    )
    return record


async def run_scheduled_backup() -> None:
    if not settings.backup_enabled:
        return
    try:
        await run_postgres_backup(trigger="scheduled")
    except Exception:
        logger.exception("Scheduled Postgres backup failed")
