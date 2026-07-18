import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.workout_template import WorkoutTemplate


class WorkoutTemplateExerciseWrite(BaseModel):
    id: uuid.UUID | None = None
    machine_id: uuid.UUID
    notes: str | None = Field(default=None, max_length=1000)


class WorkoutTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=5000)
    exercises: list[WorkoutTemplateExerciseWrite] = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Workout name cannot be empty")
        return cleaned

    @model_validator(mode="after")
    def validate_exercises(self) -> "WorkoutTemplateCreate":
        if any(item.id is not None for item in self.exercises):
            raise ValueError("New workout exercises cannot include an id")
        machine_ids = [item.machine_id for item in self.exercises]
        if len(machine_ids) != len(set(machine_ids)):
            raise ValueError("An exercise can appear only once in a saved workout")
        return self


class WorkoutTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Workout name cannot be empty")
        return cleaned


class WorkoutTemplateExercisesUpdate(BaseModel):
    exercises: list[WorkoutTemplateExerciseWrite] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_exercises(self) -> "WorkoutTemplateExercisesUpdate":
        ids = [item.id for item in self.exercises if item.id is not None]
        if len(ids) != len(set(ids)):
            raise ValueError("A saved exercise cannot appear more than once")
        machine_ids = [item.machine_id for item in self.exercises]
        if len(machine_ids) != len(set(machine_ids)):
            raise ValueError("An exercise can appear only once in a saved workout")
        return self


class WorkoutTemplateExerciseRead(BaseModel):
    id: uuid.UUID
    machine_id: uuid.UUID
    machine_name: str
    muscle_group: str
    position: int
    notes: str | None


class WorkoutTemplateRead(BaseModel):
    id: uuid.UUID
    name: str
    notes: str | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    exercises: list[WorkoutTemplateExerciseRead]

    @classmethod
    def from_model(cls, template: WorkoutTemplate) -> "WorkoutTemplateRead":
        return cls(
            id=template.id,
            name=template.name,
            notes=template.notes,
            archived_at=template.archived_at,
            created_at=template.created_at,
            updated_at=template.updated_at,
            exercises=[
                WorkoutTemplateExerciseRead(
                    id=item.id,
                    machine_id=item.machine_id,
                    machine_name=item.machine.name,
                    muscle_group=item.machine.muscle_group,
                    position=item.position,
                    notes=item.notes,
                )
                for item in sorted(template.exercises, key=lambda exercise: exercise.position)
            ],
        )
