"""Unregistered starter sketches; persistence is implemented in the Runner phase."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from frotad.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FormSubmission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "form_submissions"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    form_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    form_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    parent_submission_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    driver_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FormAnswer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "form_answers"

    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("form_submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    value_text: Mapped[str | None] = mapped_column(Text())
    value_integer: Mapped[int | None]
    value_decimal: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    value_boolean: Mapped[bool | None] = mapped_column(Boolean)
    value_date: Mapped[date | None] = mapped_column(Date)
    value_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    value_json: Mapped[dict | None] = mapped_column(JSONB)


class PeriodValue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "period_values"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("form_answers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None]
    status_key: Mapped[str | None] = mapped_column(String(80))
