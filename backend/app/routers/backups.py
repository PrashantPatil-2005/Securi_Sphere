"""Admin API for PostgreSQL backups."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import client_ip, require_roles
from app.models.user import User
from app.schemas.backup import BackupRecordResponse, BackupConfigResponse, BackupListResponse
from app.services.audit import log_audit
from app.services.backup import BackupRecord, list_backups, run_postgres_backup

router = APIRouter(prefix="/backups", tags=["backups"])


def _to_response(record: BackupRecord) -> BackupRecordResponse:
    return BackupRecordResponse(**record.to_dict())


@router.get("", response_model=BackupListResponse)
async def get_backups(user: User = Depends(require_roles("admin"))):
    import shutil

    items = [_to_response(record) for record in list_backups()]
    return BackupListResponse(
        items=items,
        config=BackupConfigResponse(
            enabled=settings.backup_enabled,
            directory=settings.backup_directory,
            retention_days=settings.backup_retention_days,
            schedule_hour=settings.backup_schedule_hour,
            pg_dump_available=shutil.which("pg_dump") is not None,
        ),
    )


@router.post("/run", response_model=BackupRecordResponse)
async def trigger_backup(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    if not settings.backup_enabled:
        raise HTTPException(status_code=400, detail="Backups are disabled (BACKUP_ENABLED=false)")
    try:
        record = await run_postgres_backup(trigger="manual")
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    await log_audit(
        db,
        "backup_triggered",
        user_id=user.id,
        ip_address=client_ip(request),
        details={"filename": record.filename, "size_bytes": record.size_bytes},
    )
    await db.commit()
    return _to_response(record)
