"""Unit tests for backup helpers."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.services.backup import (
    BackupRecord,
    _manifest_path,
    _write_manifest,
    list_backups,
    normalize_pg_url,
    prune_old_backups,
)


def test_normalize_pg_url_asyncpg():
    url = "postgresql+asyncpg://user:pass@localhost:5432/securi"
    assert normalize_pg_url(url) == "postgresql://user:pass@localhost:5432/securi"


def test_manifest_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.services.backup.settings.backup_directory", str(tmp_path))
    archive = tmp_path / "securi_pg_20260101_120000.sql.gz"
    archive.write_bytes(b"test")
    record = BackupRecord(
        filename=archive.name,
        path=str(archive),
        size_bytes=4,
        sha256="abc",
        created_at=datetime.now(timezone.utc).isoformat(),
        trigger="manual",
        duration_seconds=1.2,
        database="securi",
    )
    _write_manifest(archive, record)
    manifest = _manifest_path(archive)
    assert manifest.exists()
    loaded = json.loads(manifest.read_text(encoding="utf-8"))
    assert loaded["trigger"] == "manual"


def test_prune_old_backups(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.services.backup.settings.backup_directory", str(tmp_path))
    old = tmp_path / "securi_pg_old.sql.gz"
    old.write_bytes(b"old")
    old_time = datetime.now(timezone.utc) - timedelta(days=40)
    ts = old_time.timestamp()
    import os

    os.utime(old, (ts, ts))

    recent = tmp_path / "securi_pg_new.sql.gz"
    recent.write_bytes(b"new")

    removed = prune_old_backups(retention_days=30)
    assert old.name in removed
    assert recent.exists()
    assert not old.exists()


def test_list_backups_sorted_newest_first(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import os

    monkeypatch.setattr("app.services.backup.settings.backup_directory", str(tmp_path))
    first = tmp_path / "securi_pg_20260101_010000.sql.gz"
    second = tmp_path / "securi_pg_20260102_010000.sql.gz"
    first.write_bytes(b"a")
    second.write_bytes(b"b")
    now = datetime.now(timezone.utc).timestamp()
    os.utime(first, (now - 3600, now - 3600))
    os.utime(second, (now, now))
    items = list_backups()
    assert items[0].filename == second.name
