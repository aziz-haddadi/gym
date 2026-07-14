import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MuscleGroup(StrEnum):
    CHEST = "Chest"
    BACK = "Back"
    SHOULDERS = "Shoulders"
    ARMS = "Arms"
    LEGS = "Legs"
    CORE = "Core"
    CARDIO = "Cardio"
    FULL_BODY = "Full Body"
    OTHER = "Other"


class MachineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    muscle_group: MuscleGroup
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return " ".join(value.split())


class MachineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    muscle_group: MuscleGroup | None = None
    notes: str | None = Field(default=None, max_length=2000)
    active: bool | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value is not None else None


class MachineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    muscle_group: str
    notes: str | None
    active: bool
    created_at: datetime
    updated_at: datetime
