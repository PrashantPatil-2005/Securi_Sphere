"""Shared filtering, sorting, pagination, and time-range helpers."""
from datetime import datetime, timedelta, timezone
from enum import Enum

from fastapi import Query
from pydantic import BaseModel

TIME_PRESETS: dict[str, timedelta] = {
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "12h": timedelta(hours=12),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
}

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


class SortOrder(str, Enum):
    newest = "newest"
    oldest = "oldest"
    severity = "severity"
    risk_score = "risk_score"
    host_name = "host_name"
    alert_count = "alert_count"


class TimeRange(BaseModel):
    from_time: datetime | None = None
    to_time: datetime | None = None


def resolve_time_range(
    preset: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
) -> TimeRange:
    now = datetime.now(timezone.utc)
    if preset == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return TimeRange(from_time=start, to_time=now)
    if preset and preset in TIME_PRESETS:
        return TimeRange(from_time=now - TIME_PRESETS[preset], to_time=now)
    ft = from_time
    tt = to_time or now
    if ft and ft.tzinfo is None:
        ft = ft.replace(tzinfo=timezone.utc)
    if tt and tt.tzinfo is None:
        tt = tt.replace(tzinfo=timezone.utc)
    return TimeRange(from_time=ft, to_time=tt)


def apply_time_range(column, tr: TimeRange):
    """Return list of SQLAlchemy where clauses for a datetime column."""
    clauses = []
    if tr.from_time:
        clauses.append(column >= tr.from_time)
    if tr.to_time:
        clauses.append(column <= tr.to_time)
    return clauses


def pagination_offset(page: int, page_size: int) -> tuple[int, int]:
    return (page - 1) * page_size, page_size


class ListParams:
    """Common query parameter defaults."""

    @staticmethod
    def page() -> int:
        return Query(1, ge=1)

    @staticmethod
    def page_size() -> int:
        return Query(50, ge=1, le=500)

    @staticmethod
    def preset() -> str | None:
        return Query(None, description="Time preset: 15m,30m,1h,6h,12h,24h,7d,30d,90d")

    @staticmethod
    def from_time():
        return Query(None, alias="from")

    @staticmethod
    def to_time():
        return Query(None, alias="to")

    @staticmethod
    def sort() -> SortOrder:
        return Query(SortOrder.newest)

    @staticmethod
    def exact() -> bool:
        return Query(False, description="Exact match for search terms")
