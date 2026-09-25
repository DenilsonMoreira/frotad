import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import Mapped, mapped_column

from frotad.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Vehicle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        UniqueConstraint("company_id", "fleet_number"),
        Index("uq_vehicles_company_id_id", "company_id", "id", unique=True),
        ForeignKeyConstraint(["company_id", "branch_id"], ["branches.company_id", "branches.id"]),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    fleet_number: Mapped[str] = mapped_column(String(80), nullable=False)
    plate: Mapped[str | None] = mapped_column(String(10), index=True)
    model: Mapped[str | None] = mapped_column(String(120))
    year: Mapped[int | None] = mapped_column(Integer)
    odometer_current: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="AVAILABLE")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Driver(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "drivers"
    __table_args__ = (
        UniqueConstraint("company_id", "employee_code"),
        Index("uq_drivers_company_id_id", "company_id", "id", unique=True),
        ForeignKeyConstraint(
            ["company_id", "user_id"], ["memberships.company_id", "memberships.user_id"]
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    employee_code: Mapped[str | None] = mapped_column(String(80), index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
