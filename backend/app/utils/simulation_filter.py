"""Exclude synthetic simulation events from production dashboard queries."""
from sqlalchemy import or_

from app.config import settings
from app.models.event import Event


def real_events_only():
    """SQLAlchemy clause: event was not injected by the simulation feature."""
    return or_(Event.source.is_(None), Event.source != "simulation")


def should_exclude_simulated(include_simulated: bool | None = None) -> bool:
    if include_simulated is True:
        return False
    if include_simulated is False:
        return True
    return settings.exclude_simulated_from_dashboard
