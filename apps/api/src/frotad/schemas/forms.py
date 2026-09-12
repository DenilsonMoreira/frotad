from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from frotad.models.forms import FieldType


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FormCreate(StrictInput):
    code: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(None, max_length=4000)


class PeriodConfig(StrictInput):
    status_key: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    status_label: str = Field(min_length=1, max_length=200)
    allow_concurrent: bool = False
    capture_location_on_start: bool = False
    capture_location_on_end: bool = False


class SelectConfig(StrictInput):
    options: list[str] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def valid_options(self):
        if any(not option.strip() or len(option) > 200 for option in self.options):
            raise ValueError("options must be nonempty strings of at most 200 characters")
        if len(set(self.options)) != len(self.options):
            raise ValueError("duplicate options")
        return self


class EvidenceConfig(StrictInput):
    policy: str = Field(
        default="OPTIONAL", pattern="^(DISABLED|OPTIONAL|REQUIRED|REQUIRED_ON_ISSUE)$"
    )


class CalculatedConfig(StrictInput):
    expression: dict

    @model_validator(mode="after")
    def safe_expression(self):
        from frotad.services.formulas import validate

        validate(self.expression)
        return self


class SubformConfig(StrictInput):
    form_version_id: UUID


class FieldCreate(StrictInput):
    key: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    label: str = Field(min_length=1, max_length=200)
    field_type: FieldType
    required: bool = False
    config: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_config(self):
        schema = {
            FieldType.PERIOD: PeriodConfig,
            FieldType.CALCULATED: CalculatedConfig,
            FieldType.SUBFORM: SubformConfig,
            FieldType.SINGLE_SELECT: SelectConfig,
            FieldType.MULTI_SELECT: SelectConfig,
            FieldType.FILE: EvidenceConfig,
            FieldType.PHOTO: EvidenceConfig,
        }.get(self.field_type, StrictInput)
        self.config = schema.model_validate(self.config).model_dump(mode="json")
        return self


class ReorderFields(StrictInput):
    field_ids: list[UUID] = Field(max_length=200)

    @model_validator(mode="after")
    def unique_ids(self):
        if len(set(self.field_ids)) != len(self.field_ids):
            raise ValueError("duplicate field IDs")
        return self


class FieldRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    key: str
    label: str
    field_type: FieldType
    position: int
    required: bool
    config: dict


class VersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    form_id: UUID
    version: int
    name: str
    description: str | None
    published_at: datetime | None
    schema_hash: str | None
    fields: list[FieldRead]
