import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from frotad.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FormSubmission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "form_submissions"
    __table_args__ = (
        UniqueConstraint("id", "form_version_id", name="uq_submission_id_version"),
        UniqueConstraint("id", "company_id", name="uq_submission_id_company"),
        ForeignKeyConstraint(["company_id", "form_id"], ["forms.company_id", "forms.id"]),
        ForeignKeyConstraint(
            ["form_id", "form_version_id"], ["form_versions.form_id", "form_versions.id"]
        ),
        ForeignKeyConstraint(["company_id", "vehicle_id"], ["vehicles.company_id", "vehicles.id"]),
        ForeignKeyConstraint(["company_id", "driver_id"], ["drivers.company_id", "drivers.id"]),
        ForeignKeyConstraint(["company_id", "branch_id"], ["branches.company_id", "branches.id"]),
        CheckConstraint("status IN ('DRAFT', 'SUBMITTED')", name="submission_status"),
    )
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    form_id: Mapped[uuid.UUID]
    form_version_id: Mapped[uuid.UUID]
    vehicle_id: Mapped[uuid.UUID | None]
    driver_id: Mapped[uuid.UUID | None]
    branch_id: Mapped[uuid.UUID | None]
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    timezone: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FormAnswer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "form_answers"
    __table_args__ = (
        UniqueConstraint("submission_id", "field_id"),
        UniqueConstraint("id", "submission_id", "company_id"),
        ForeignKeyConstraint(
            ["submission_id", "form_version_id"],
            ["form_submissions.id", "form_submissions.form_version_id"],
            name="fk_answer_submission_version",
        ),
        ForeignKeyConstraint(
            ["submission_id", "company_id"],
            ["form_submissions.id", "form_submissions.company_id"],
            name="fk_answer_submission_company",
        ),
        ForeignKeyConstraint(
            ["form_version_id", "field_id"], ["form_fields.form_version_id", "form_fields.id"]
        ),
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(index=True)
    company_id: Mapped[uuid.UUID]
    form_version_id: Mapped[uuid.UUID]
    field_id: Mapped[uuid.UUID]
    value_text: Mapped[str | None] = mapped_column(Text)
    value_integer: Mapped[int | None]
    value_decimal: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    value_boolean: Mapped[bool | None] = mapped_column(Boolean)
    value_date: Mapped[date | None] = mapped_column(Date)
    value_time: Mapped[time | None] = mapped_column(Time)
    value_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    value_json: Mapped[list | None] = mapped_column(JSON().with_variant(JSONB(), "postgresql"))


class PeriodValue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "period_values"
    __table_args__ = (
        ForeignKeyConstraint(
            ["answer_id", "submission_id", "company_id"],
            ["form_answers.id", "form_answers.submission_id", "form_answers.company_id"],
        ),
        CheckConstraint("end_at IS NULL OR end_at >= start_at", name="period_chronology"),
        CheckConstraint(
            "(end_at IS NULL AND duration_seconds IS NULL) OR (end_at IS NOT NULL AND duration_seconds IS NOT NULL AND duration_seconds >= 0)",
            name="period_duration",
        ),
    )
    company_id: Mapped[uuid.UUID] = mapped_column(index=True)
    submission_id: Mapped[uuid.UUID] = mapped_column(index=True)
    answer_id: Mapped[uuid.UUID] = mapped_column(unique=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None]
    status_key: Mapped[str] = mapped_column(String(80))
    allow_concurrent: Mapped[bool] = mapped_column(Boolean)


class SubmissionRelation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "submission_relations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["parent_submission_id", "company_id"],
            ["form_submissions.id", "form_submissions.company_id"],
            name="fk_relation_parent_company",
        ),
        ForeignKeyConstraint(
            ["child_submission_id", "company_id"],
            ["form_submissions.id", "form_submissions.company_id"],
            name="fk_relation_child_company",
        ),
        ForeignKeyConstraint(
            ["parent_submission_id", "parent_version_id"],
            ["form_submissions.id", "form_submissions.form_version_id"],
            name="fk_relation_parent_version",
        ),
        ForeignKeyConstraint(
            ["parent_version_id", "relation_field_id"],
            ["form_fields.form_version_id", "form_fields.id"],
            name="fk_relation_field_version",
        ),
        UniqueConstraint("child_submission_id"),
        UniqueConstraint("parent_submission_id", "request_key"),
        CheckConstraint("parent_submission_id <> child_submission_id", name="relation_not_self"),
    )
    company_id: Mapped[uuid.UUID] = mapped_column(index=True)
    parent_submission_id: Mapped[uuid.UUID] = mapped_column(index=True)
    child_submission_id: Mapped[uuid.UUID]
    parent_version_id: Mapped[uuid.UUID]
    relation_field_id: Mapped[uuid.UUID]
    request_key: Mapped[uuid.UUID]
