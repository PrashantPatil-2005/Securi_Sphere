"""Exclude synthetic simulation events from production dashboard queries."""
from fastapi import Query
from sqlalchemy import exists, or_, select

from app.config import settings
from app.models.alert import Alert
from app.models.event import Event
from app.models.siem import Offense, OffenseEvent


def include_simulated_param() -> bool | None:
    return Query(
        None,
        description="When true, include Attack Lab simulation data in this response",
    )


def real_events_only():
    """SQLAlchemy clause: event was not injected by the simulation feature."""
    return or_(Event.source.is_(None), Event.source != "simulation")


def real_alerts_only():
    """SQLAlchemy clause: alert was not generated from simulation events."""
    return or_(Alert.source.is_(None), Alert.source != "simulation")


def real_offenses_only():
    """SQLAlchemy clause: offense is not linked to simulation events or alerts."""
    return ~exists(
        select(1)
        .select_from(OffenseEvent)
        .outerjoin(Event, OffenseEvent.event_id == Event.id)
        .outerjoin(Alert, OffenseEvent.alert_id == Alert.id)
        .where(
            OffenseEvent.offense_id == Offense.id,
            or_(Event.source == "simulation", Alert.source == "simulation"),
        )
    )


def should_exclude_simulated(include_simulated: bool | None = None) -> bool:
    if include_simulated is True:
        return False
    if include_simulated is False:
        return True
    return settings.exclude_simulated_from_dashboard
