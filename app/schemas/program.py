import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.muscles import MuscleGroup
from app.domain.programs import ProgramStepType
from app.models.program import WorkoutProgram, WorkoutProgramStep


class ProgramStepWrite(BaseModel):
    id: uuid.UUID | None = None
    step_type: ProgramStepType
    label: str | None = Field(default=None, max_length=100)
    muscle_groups: list[MuscleGroup] | None = Field(default=None, max_length=10)
    linked_workout_template_id: uuid.UUID | None = None

    @field_validator("label")
    @classmethod
    def clean_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None

    @field_validator("muscle_groups")
    @classmethod
    def unique_muscle_groups(
        cls, value: list[MuscleGroup] | None
    ) -> list[MuscleGroup] | None:
        if value is None:
            return None
        return list(dict.fromkeys(value)) or None

    @model_validator(mode="after")
    def validate_step(self) -> "ProgramStepWrite":
        if self.step_type == ProgramStepType.WORKOUT and not self.label:
            raise ValueError("Workout steps require a label")
        if self.step_type == ProgramStepType.REST:
            self.muscle_groups = None
            self.linked_workout_template_id = None
        return self


class ProgramCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    advance_on_any_workout: bool = True
    starts_on: date | None = None
    steps: list[ProgramStepWrite] = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Program name cannot be empty")
        return cleaned

    @model_validator(mode="after")
    def reject_step_ids(self) -> "ProgramCreate":
        if any(step.id is not None for step in self.steps):
            raise ValueError("New program steps cannot include an id")
        return self


class ProgramUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    advance_on_any_workout: bool | None = None
    starts_on: date | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Program name cannot be empty")
        return cleaned

    @field_validator("starts_on")
    @classmethod
    def require_start_date(cls, value: date | None) -> date:
        if value is None:
            raise ValueError("Program start date cannot be empty")
        return value


class ProgramStepsUpdate(BaseModel):
    steps: list[ProgramStepWrite] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_step_ids(self) -> "ProgramStepsUpdate":
        ids = [step.id for step in self.steps if step.id is not None]
        if len(ids) != len(set(ids)):
            raise ValueError("A program step cannot appear more than once")
        return self


class ProgramAdvanceRequest(BaseModel):
    target_step_id: uuid.UUID | None = None


class ProgramActivateRequest(BaseModel):
    starts_on: date | None = None


class ProgramStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    position: int
    step_type: str
    label: str | None
    muscle_groups: list[str] | None
    linked_workout_template_id: uuid.UUID | None
    linked_workout_template_name: str | None

    @classmethod
    def from_model(cls, step: WorkoutProgramStep) -> "ProgramStepRead":
        return cls(
            id=step.id,
            position=step.position,
            step_type=step.step_type,
            label=step.label,
            muscle_groups=step.muscle_groups,
            linked_workout_template_id=step.linked_workout_template_id,
            linked_workout_template_name=(
                step.linked_workout_template.name if step.linked_workout_template else None
            ),
        )


class ProgramCycleStateRead(BaseModel):
    current_step_id: uuid.UUID
    current_position: int
    last_advanced_date: date


class ProgramRead(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool
    advance_on_any_workout: bool
    starts_on: date
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    steps: list[ProgramStepRead]
    cycle_state: ProgramCycleStateRead | None

    @classmethod
    def from_model(cls, program: WorkoutProgram) -> "ProgramRead":
        steps = sorted(program.steps, key=lambda item: item.position)
        position_by_id = {step.id: step.position for step in steps}
        state = program.cycle_state
        return cls(
            id=program.id,
            name=program.name,
            is_active=program.is_active,
            advance_on_any_workout=program.advance_on_any_workout,
            starts_on=program.starts_on,
            archived_at=program.archived_at,
            created_at=program.created_at,
            updated_at=program.updated_at,
            steps=[ProgramStepRead.from_model(step) for step in steps],
            cycle_state=(
                ProgramCycleStateRead(
                    current_step_id=state.current_step_id,
                    current_position=position_by_id.get(state.current_step_id, 0),
                    last_advanced_date=state.last_advanced_date,
                )
                if state
                else None
            ),
        )


class ProgramDueRead(BaseModel):
    program_id: uuid.UUID
    program_name: str
    advance_on_any_workout: bool
    starts_on: date
    is_started: bool
    step: ProgramStepRead
    last_advanced_date: date

    @classmethod
    def from_models(
        cls,
        program: WorkoutProgram,
        step: WorkoutProgramStep,
        last_advanced_date: date,
        is_started: bool,
    ) -> "ProgramDueRead":
        return cls(
            program_id=program.id,
            program_name=program.name,
            advance_on_any_workout=program.advance_on_any_workout,
            starts_on=program.starts_on,
            is_started=is_started,
            step=ProgramStepRead.from_model(step),
            last_advanced_date=last_advanced_date,
        )
