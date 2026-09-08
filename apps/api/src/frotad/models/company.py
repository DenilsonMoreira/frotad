import uuid

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import Mapped, mapped_column

from frotad.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="America/Fortaleza")


class Branch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "branches"
    __table_args__ = (UniqueConstraint("company_id", "id"),)

    timezone: Mapped[str | None] = mapped_column(String(64))

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
