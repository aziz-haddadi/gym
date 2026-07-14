import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.workout import Workout


class WorkoutSetWrite(BaseModel):
    reps: int = Field(ge=1, le=1000)
    weight_kg: Decimal = Field(ge=0, le=100000, decimal_places=2)
    rpe: Decimal | None = Field(default=None, ge=1, le=10, decimal_places=1)
    is_drop_set: bool = False


class WorkoutEntryWrite(BaseModel):
    machine_id: uuid.UUID
    notes: str | None = Field(default=None, max_length=1000)
    sets: list[WorkoutSetWrite] = Field(default_factory=list, max_length=100)


class WorkoutCreate(BaseModel):
    workout_date: date
    title: str = Field(default="Workout", min_length=1, max_length=100)
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    notes: str | None = Field(default=None, max_length=5000)
    entries: list[WorkoutEntryWrite] = Field(default_factory=list, max_length=100)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        return " ".join(value.split())


class WorkoutUpdate(BaseModel):
    workout_date: date | None = None
    title: str | None = Field(default=None, min_length=1, max_length=100)
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    notes: str | None = Field(default=None, max_length=5000)
    entries: list[WorkoutEntryWrite] | None = Field(default=None, max_length=100)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value is not None else None


class WorkoutSetRead(BaseModel):
    id: uuid.UUID
    set_number: int
    reps: int
    weight_kg: Decimal
    rpe: Decimal | None
    is_drop_set: bool


class WorkoutEntryRead(BaseModel):
    id: uuid.UUID
    machine_id: uuid.UUID
    machine_name: str
    muscle_group: str
    position: int
    notes: str | None
    sets: list[WorkoutSetRead]


class WorkoutRead(BaseModel):
    id: uuid.UUID
    workout_date: date
    title: str
    duration_minutes: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    entries: list[WorkoutEntryRead]
    total_sets: int
    drop_sets: int
    total_volume_kg: Decimal

    @classmethod
    def from_model(cls, workout: Workout) -> "WorkoutRead":
        entries = [
            WorkoutEntryRead(
                id=entry.id,
                machine_id=entry.machine_id,
                machine_name=entry.machine.name,
                muscle_group=entry.machine.muscle_group,
                position=entry.position,
                notes=entry.notes,
                sets=[
                    WorkoutSetRead(
                        id=item.id,
                        set_number=item.set_number,
                        reps=item.reps,
                        weight_kg=item.weight_kg,
                        rpe=item.rpe,
                        is_drop_set=item.is_drop_set,
                    )
                    for item in entry.sets
                ],
            )
            for entry in workout.entries
        ]
        all_sets = [item for entry in workout.entries for item in entry.sets]
        volume = sum((item.weight_kg * item.reps for item in all_sets), start=Decimal("0"))
        return cls(
            id=workout.id,
            workout_date=workout.workout_date,
            title=workout.title,
            duration_minutes=workout.duration_minutes,
            notes=workout.notes,
            created_at=workout.created_at,
            updated_at=workout.updated_at,
            entries=entries,
            total_sets=len(all_sets),
            drop_sets=sum(item.is_drop_set for item in all_sets),
            total_volume_kg=volume,
        )


class WorkoutPage(BaseModel):
    items: list[WorkoutRead]
    total: int
    limit: int
    offset: int
