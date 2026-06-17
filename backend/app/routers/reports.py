import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.alert import Alert
from app.models.host import Host
from app.models.threat_score import HostThreatScore
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary")
async def report_summary(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    format: str = Query("json"),
):
    hosts = (await db.execute(select(func.count()).select_from(Host))).scalar_one()
    alerts = (await db.execute(select(func.count()).select_from(Alert).where(Alert.status == "open"))).scalar_one()
    scores = list((await db.execute(select(HostThreatScore).order_by(HostThreatScore.score.desc()))).scalars().all())
    data = {"total_hosts": hosts, "open_alerts": alerts, "threat_scores": [{"host_id": str(s.host_id), "score": s.score} for s in scores]}
    if format == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["host_id", "threat_score"])
        for s in scores:
            w.writerow([str(s.host_id), s.score])
        return Response(content=buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=report.csv"})
    return data
