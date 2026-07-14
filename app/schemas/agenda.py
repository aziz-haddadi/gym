import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgendaDayWrite(BaseModel):
    workout_name: str = Field(min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("workout_name")
    @classmethod
    def clean_workout_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class AgendaDayRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    day_of_week: int
    workout_name: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
