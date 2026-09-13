from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

from frotad.models.identity import Role


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def email_normalized(cls, value):
        value = value.strip().lower()
        if value.count("@") != 1 or any(c.isspace() for c in value):
            raise ValueError("invalid email")
        local, domain = value.split("@")
        if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
            raise ValueError("invalid email")
        return value


class Register(Login):
    password: str = Field(min_length=15, max_length=128)
    name: str = Field(min_length=1, max_length=200)
    company_name: str = Field(min_length=1, max_length=200)
    company_slug: str = Field(min_length=3, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    timezone: str = Field(default="America/Fortaleza", max_length=64)

    @field_validator("name", "company_name")
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError("required")
        return value.strip()

    @field_validator("timezone")
    @classmethod
    def valid_zone(cls, value):
        try:
            ZoneInfo(value)
        except ValueError, ZoneInfoNotFoundError:
            raise ValueError("invalid timezone") from None
        return value


class UserCreate(Login):
    password: str = Field(min_length=15, max_length=128)
    name: str = Field(min_length=1, max_length=200)
    role: Role = Role.VIEWER

    @field_validator("name")
    @classmethod
    def name_required(cls, value):
        if not value.strip():
            raise ValueError("required")
        return value.strip()


class UserRead(BaseModel):
    id: UUID
    name: str
    email: str
    role: Role | None
    active: bool


class SessionRead(BaseModel):
    user: UserRead
    company_id: UUID | None
    company_name: str | None
    is_system_admin: bool = False


class LoginRead(SessionRead):
    access_token: str
    expires_at: datetime


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    active: bool


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=15, max_length=128)


class CompanyRead(BaseModel):
    id: UUID
    name: str
    slug: str
    timezone: str
