from pydantic import BaseModel, Field


class DashboardWidget(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    visible: bool = True


class DashboardLayoutResponse(BaseModel):
    widgets: list[DashboardWidget]


class DashboardLayoutUpdate(BaseModel):
    widgets: list[DashboardWidget] = Field(min_length=1)
