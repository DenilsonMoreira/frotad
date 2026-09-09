import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from frotad.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FormStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class FieldType(str, enum.Enum):
    TEXT = "TEXT"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    DATE = "DATE"
    TIME = "TIME"
    DATETIME = "DATETIME"
    BOOLEAN = "BOOLEAN"
    SINGLE_SELECT = "SINGLE_SELECT"
    MULTI_SELECT = "MULTI_SELECT"
    VEHICLE_REFERENCE = "VEHICLE_REFERENCE"
    DRIVER_REFERENCE = "DRIVER_REFERENCE"
    CUSTOMER_REFERENCE = "CUSTOMER_REFERENCE"
    JOBSITE_REFERENCE = "JOBSITE_REFERENCE"
    PHOTO = "PHOTO"
    FILE = "FILE"
    PERIOD = "PERIOD"
    CALCULATED = "CALCULATED"
    SUBFORM = "SUBFORM"


class Form(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "forms"
    __table_args__ = (
        UniqueConstraint("company_id", "code"),
        Index("uq_forms_company_id_id", "company_id", "id", unique=True),
    )
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[FormStatus] = mapped_column(
        Enum(FormStatus, native_enum=False), default=FormStatus.DRAFT
    )


class FormVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "form_versions"
    __table_args__ = (
        UniqueConstraint("form_id", "version"),
        Index("uq_form_versions_form_id_id", "form_id", "id", unique=True),
        Index(
            "uq_form_versions_draft",
            "form_id",
            unique=True,
            postgresql_where=text("published_at IS NULL"),
            sqlite_where=text("published_at IS NULL"),
        ),
    )
    form_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("forms.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    schema_hash: Mapped[str | None] = mapped_column(String(64))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))


class FormField(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "form_fields"
    __table_args__ = (
        UniqueConstraint("form_version_id", "key"),
        Index("uq_form_fields_version_id_id", "form_version_id", "id", unique=True),
    )
    form_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("form_versions.id"), index=True)
    key: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(200))
    field_type: Mapped[FieldType] = mapped_column(Enum(FieldType, native_enum=False))
    position: Mapped[int] = mapped_column(Integer)
    required: Mapped[bool] = mapped_column(default=False)
    config: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), default=dict)
