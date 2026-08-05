"""Backup schemas."""

from pydantic import BaseModel


class BackupRecordResponse(BaseModel):
    filename: str
    path: str
    size_bytes: int
    sha256: str
    created_at: str
    trigger: str
    duration_seconds: float
    database: str
    status: str
    error: str | None = None


class BackupConfigResponse(BaseModel):
    enabled: bool
    directory: str
    retention_days: int
    schedule_hour: int
    pg_dump_available: bool


class BackupListResponse(BaseModel):
    items: list[BackupRecordResponse]
    config: BackupConfigResponse
