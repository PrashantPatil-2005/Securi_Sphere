from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MetricResponse(BaseModel):
    id: UUID
    host_id: UUID
    cpu_percent: float | None
    memory_percent: float | None
    disk_percent: float | None
    network_in: int | None
    network_out: int | None
    load_average: list[float] | None
    uptime_seconds: int | None
    recorded_at: datetime

    model_config = {"from_attributes": True}
