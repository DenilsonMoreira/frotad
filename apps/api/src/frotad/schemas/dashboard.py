from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class DashboardConfig(BaseModel):
    cycle_form: str = "FORM02"
    volume_field: str = "volume_m3"
    fuel_form: str = "FORM03"
    fuel_field: str = "liters"
    waiting_status: str = "WAITING_AT_SITE"
    target_liters_per_m3: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)


class DailyMetrics(BaseModel):
    day: date
    trips: int = 0
    volume_m3: Decimal = Decimal(0)
    diesel_liters: Decimal = Decimal(0)
    liters_per_m3: Decimal | None = None
    missing_measurements: int = 0


class LiveOperation(BaseModel):
    period_id: UUID
    submission_id: UUID
    vehicle: str
    driver: str
    status_key: str
    status_label: str
    started_at: datetime
    elapsed_seconds: int


class DashboardRead(BaseModel):
    company: str
    timezone: str
    server_time: datetime
    metrics: DailyMetrics
    trend: list[DailyMetrics]
    active: list[LiveOperation]
    active_vehicles: int
    active_cycles: int
    waiting: int
    waiting_status: str
    target_liters_per_m3: Decimal | None
