from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class WorkerPreferencesRead(BaseModel):
    category_ids: list[int] = Field(default_factory=list)
    metro_station_ids: list[int] = Field(default_factory=list)
    min_hourly_rate: Decimal | None = None
    notifications_enabled: bool = True

    model_config = {"from_attributes": True}


class WorkerPreferencesUpdate(BaseModel):
    category_ids: list[int] | None = None
    metro_station_ids: list[int] | None = None
    min_hourly_rate: Decimal | None = Field(default=None, ge=0)
    notifications_enabled: bool | None = None


class WorkerNotificationsToggle(BaseModel):
    notifications_enabled: bool
