from pydantic import BaseModel

from app.schemas.alert import AlertResponse
from app.schemas.event import EventResponse
from app.schemas.host import HostResponse


class SearchResponse(BaseModel):
    hosts: list[HostResponse]
    alerts: list[AlertResponse]
    events: list[EventResponse]
    query: str
