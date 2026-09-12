from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from frotad.schemas.forms import FieldRead, StrictInput


class SubmissionCreate(StrictInput):
    form_version_id: UUID
    vehicle_id: UUID | None = None
    driver_id: UUID | None = None
    branch_id: UUID | None = None


class AnswerWrite(StrictInput):
    value: Any


class EmptyCommand(StrictInput):
    pass


class PeriodRead(BaseModel):
    field_id: UUID
    start_at: datetime
    end_at: datetime | None
    duration_seconds: int
    status_key: str
    status: str


class AnswerRead(BaseModel):
    field_id: UUID
    value: Any


class ChildCreate(StrictInput):
    request_key: UUID


class ChildRead(BaseModel):
    field_id: UUID
    submission_id: UUID
    status: str


class SubmissionRead(BaseModel):
    id: UUID
    form_version_id: UUID
    form_name: str
    fields: list[FieldRead]
    vehicle_id: UUID | None
    driver_id: UUID | None
    branch_id: UUID | None
    timezone: str
    status: str
    started_at: datetime
    submitted_at: datetime | None
    server_time: datetime
    answers: list[AnswerRead] = Field(default_factory=list)
    periods: list[PeriodRead] = Field(default_factory=list)

    children: list[ChildRead] = Field(default_factory=list)
