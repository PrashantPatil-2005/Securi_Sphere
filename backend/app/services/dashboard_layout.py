from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dashboard import DEFAULT_WIDGETS, DashboardLayout
from app.models.user import User
from app.schemas.dashboard import DashboardLayoutResponse, DashboardLayoutUpdate, DashboardWidget


def _normalize_widgets(widgets: list[DashboardWidget]) -> list[dict]:
    seen: set[str] = set()
    normalized: list[dict] = []
    for w in widgets:
        if w.id in seen:
            continue
        seen.add(w.id)
        normalized.append({"id": w.id, "visible": w.visible})
    return normalized


async def get_dashboard_layout(db: AsyncSession, user: User) -> DashboardLayoutResponse:
    row = (
        await db.execute(select(DashboardLayout).where(DashboardLayout.user_id == user.id))
    ).scalar_one_or_none()
    if not row:
        return DashboardLayoutResponse(widgets=[DashboardWidget(**w) for w in DEFAULT_WIDGETS])
    return DashboardLayoutResponse(
        widgets=[DashboardWidget(id=w["id"], visible=bool(w.get("visible", True))) for w in row.widgets]
    )


async def update_dashboard_layout(
    db: AsyncSession, user: User, body: DashboardLayoutUpdate
) -> DashboardLayoutResponse:
    widgets = _normalize_widgets(body.widgets)
    row = (
        await db.execute(select(DashboardLayout).where(DashboardLayout.user_id == user.id))
    ).scalar_one_or_none()
    if row:
        row.widgets = widgets
        row.updated_at = datetime.now(timezone.utc)
    else:
        row = DashboardLayout(user_id=user.id, widgets=widgets)
        db.add(row)
    await db.commit()
    await db.refresh(row)
    return DashboardLayoutResponse(
        widgets=[DashboardWidget(id=w["id"], visible=bool(w.get("visible", True))) for w in row.widgets]
    )


async def pin_saved_search_widget(db: AsyncSession, user: User, search_id: UUID) -> DashboardLayoutResponse:
    widget_id = f"saved_search:{search_id}"
    current = await get_dashboard_layout(db, user)
    widgets = [w.model_dump() for w in current.widgets]
    if not any(w["id"] == widget_id for w in widgets):
        widgets.append({"id": widget_id, "visible": True})
    return await update_dashboard_layout(
        db, user, DashboardLayoutUpdate(widgets=[DashboardWidget(**w) for w in widgets])
    )
