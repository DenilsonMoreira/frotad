from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VehicleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    branch_id: UUID | None
    fleet_number: str
    plate: str | None
    status: str
    odometer_current: Decimal | None


class DriverRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    user_id: UUID | None
    name: str
    active: bool
