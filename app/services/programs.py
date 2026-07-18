from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.domain.programs import ProgramStepType
from app.models.base import utc_now
from app.models.program import WorkoutProgram, WorkoutProgramCycleState, WorkoutProgramStep
from app.models.user import User
from app.repositories.programs import WorkoutProgramRepository
from app.schemas.program import ProgramCreate, ProgramStepsUpdate, ProgramStepWrite, ProgramUpdate
from app.services.exceptions import InputError, NotFoundError
from app.services.time import local_today
from app.services.workout_templates import WorkoutTemplateService


@dataclass(frozen=True)
class DueProgramStep:
    program: WorkoutProgram
    step: WorkoutProgramStep
    last_advanced_date: date
    is_started: bool


class WorkoutProgramService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = WorkoutProgramRepository(db)
        self.templates = WorkoutTemplateService(db)

    def _validate_linked_templates(
        self, user: User, steps: list[ProgramStepWrite]
    ) -> None:
        for step in steps:
            if step.linked_workout_template_id:
                self.templates.get_loggable(user, step.linked_workout_template_id)

    def list_programs(
        self, user: User, *, include_archived: bool = False
    ) -> list[WorkoutProgram]:
        return self.repository.list_for_user(user.id, include_archived=include_archived)

    def get(self, user: User, program_id: uuid.UUID) -> WorkoutProgram:
        program = self.repository.get_for_user(program_id, user.id)
        if not program:
            raise NotFoundError("Workout program not found")
        return program

    @staticmethod
    def _step_model(
        program_id: uuid.UUID, position: int, data: ProgramStepWrite
    ) -> WorkoutProgramStep:
        return WorkoutProgramStep(
            program_id=program_id,
            position=position,
            step_type=data.step_type.value,
            label=data.label,
            muscle_groups=(
                [group.value for group in data.muscle_groups]
                if data.muscle_groups
                else None
            ),
            linked_workout_template_id=data.linked_workout_template_id,
        )

    @staticmethod
    def _apply_step(
        step: WorkoutProgramStep, position: int, data: ProgramStepWrite
    ) -> None:
        step.position = position
        step.step_type = data.step_type.value
        step.label = data.label
        step.muscle_groups = (
            [group.value for group in data.muscle_groups] if data.muscle_groups else None
        )
        step.linked_workout_template_id = data.linked_workout_template_id

    @staticmethod
    def _ordered_steps(program: WorkoutProgram) -> list[WorkoutProgramStep]:
        steps = sorted(program.steps, key=lambda item: item.position)
        if not steps:
            raise InputError("A workout program must contain at least one step")
        return steps

    @staticmethod
    def _current_step(
        program: WorkoutProgram, steps: list[WorkoutProgramStep]
    ) -> WorkoutProgramStep:
        state = program.cycle_state
        if state:
            for step in steps:
                if step.id == state.current_step_id:
                    return step
        raise InputError("Workout program cycle state is invalid")

    @staticmethod
    def _next_step(
        steps: list[WorkoutProgramStep], current: WorkoutProgramStep
    ) -> WorkoutProgramStep:
        index = next(index for index, step in enumerate(steps) if step.id == current.id)
        return steps[(index + 1) % len(steps)]

    @staticmethod
    def _assert_editable(program: WorkoutProgram) -> None:
        if program.archived_at is not None:
            raise InputError("Archived workout programs cannot be edited")

    def create(self, user: User, data: ProgramCreate) -> WorkoutProgram:
        self._validate_linked_templates(user, data.steps)
        program = WorkoutProgram(
            user_id=user.id,
            name=data.name,
            advance_on_any_workout=data.advance_on_any_workout,
            starts_on=data.starts_on or local_today(user.timezone),
        )
        self.db.add(program)
        self.db.flush()
        program.steps = [
            self._step_model(program.id, position, step)
            for position, step in enumerate(data.steps)
        ]
        self.repository.add(program)
        self.db.commit()
        return self.repository.refresh_graph(program)

    def update(
        self, user: User, program_id: uuid.UUID, data: ProgramUpdate
    ) -> WorkoutProgram:
        program = self.repository.get_for_user(program_id, user.id, for_update=True)
        if not program:
            raise NotFoundError("Workout program not found")
        self._assert_editable(program)
        changes = data.model_dump(exclude_unset=True)
        starts_on_changed = "starts_on" in changes and changes["starts_on"] != program.starts_on
        for field, value in changes.items():
            setattr(program, field, value)
        if starts_on_changed and program.is_active:
            steps = self._ordered_steps(program)
            program.cycle_state.current_step = steps[0]  # type: ignore[union-attr]
            program.cycle_state.last_advanced_date = program.starts_on  # type: ignore[union-attr]
        self.db.commit()
        return self.repository.refresh_graph(program)

    def update_steps(
        self, user: User, program_id: uuid.UUID, data: ProgramStepsUpdate
    ) -> WorkoutProgram:
        program = self.repository.get_for_user(program_id, user.id, for_update=True)
        if not program:
            raise NotFoundError("Workout program not found")
        self._assert_editable(program)
        self._validate_linked_templates(user, data.steps)

        old_steps = self._ordered_steps(program)
        old_by_id = {step.id: step for step in old_steps}
        requested_ids = {step.id for step in data.steps if step.id is not None}
        unknown_ids = requested_ids.difference(old_by_id)
        if unknown_ids:
            raise InputError("One or more program steps do not belong to this program")

        state = program.cycle_state
        old_current_id = state.current_step_id if state else None
        old_current_type = old_by_id[old_current_id].step_type if old_current_id else None

        # Move persisted rows out of the final position range first. This avoids
        # transient unique-key collisions when two existing steps swap places.
        for offset, step in enumerate(old_steps, start=1000):
            step.position = offset
        self.db.flush()

        new_steps: list[WorkoutProgramStep] = []
        for position, step_data in enumerate(data.steps):
            step = (
                old_by_id[step_data.id]
                if step_data.id is not None
                else self._step_model(program.id, position, step_data)
            )
            self._apply_step(step, position, step_data)
            new_steps.append(step)

        if state:
            current = next((step for step in new_steps if step.id == old_current_id), None)
            if current is None:
                old_index = next(
                    index for index, step in enumerate(old_steps) if step.id == old_current_id
                )
                surviving_ids = {step.id for step in new_steps if step.id is not None}
                for distance in range(1, len(old_steps) + 1):
                    candidate = old_steps[(old_index + distance) % len(old_steps)]
                    if candidate.id in surviving_ids:
                        current = candidate
                        break
                current = current or new_steps[0]
                state.current_step = current
                state.last_advanced_date = max(
                    local_today(user.timezone), program.starts_on
                )
            elif old_current_type != current.step_type:
                state.last_advanced_date = max(
                    local_today(user.timezone), program.starts_on
                )

        program.steps = new_steps
        self.db.commit()
        return self.repository.refresh_graph(program)

    def archive(self, user: User, program_id: uuid.UUID) -> None:
        program = self.repository.get_for_user(program_id, user.id, for_update=True)
        if not program:
            raise NotFoundError("Workout program not found")
        if program.archived_at is None:
            program.is_active = False
            program.archived_at = utc_now()
            self.db.commit()

    def activate(
        self,
        user: User,
        program_id: uuid.UUID,
        *,
        starts_on: date | None = None,
    ) -> WorkoutProgram:
        # Lock every candidate in a deterministic order before selecting the
        # target. Concurrent activation requests therefore cannot lock two
        # different targets first and deadlock while deactivating each other.
        programs = self.repository.lock_all_for_user(user.id)
        program = next((item for item in programs if item.id == program_id), None)
        if not program:
            raise NotFoundError("Workout program not found")
        program = self.repository.get_for_user(program_id, user.id)  # load step graph
        if not program:  # pragma: no cover - locked row cannot disappear
            raise NotFoundError("Workout program not found")
        self._assert_editable(program)
        steps = self._ordered_steps(program)

        for item in programs:
            item.is_active = False
        self.db.flush()

        program.is_active = True
        program.starts_on = starts_on or program.starts_on or local_today(user.timezone)
        if program.cycle_state:
            program.cycle_state.current_step = steps[0]
            program.cycle_state.last_advanced_date = program.starts_on
        else:
            program.cycle_state = WorkoutProgramCycleState(
                program_id=program.id,
                current_step=steps[0],
                last_advanced_date=program.starts_on,
            )
        self.db.commit()
        return self.repository.refresh_graph(program)

    def _resolve_due(self, user: User) -> DueProgramStep | None:
        program = self.repository.get_active_for_user(user.id, for_update=True)
        if not program:
            return None
        steps = self._ordered_steps(program)
        today = local_today(user.timezone)

        if not program.cycle_state:
            program.cycle_state = WorkoutProgramCycleState(
                program_id=program.id,
                current_step=steps[0],
                last_advanced_date=program.starts_on,
            )
            current = steps[0]
        else:
            current = self._current_step(program, steps)

        state = program.cycle_state
        is_started = today >= program.starts_on
        if not is_started:
            return DueProgramStep(
                program=program,
                step=current,
                last_advanced_date=state.last_advanced_date,
                is_started=False,
            )
        if (
            current.step_type == ProgramStepType.REST.value
            and state.last_advanced_date < today
            and all(step.step_type == ProgramStepType.REST.value for step in steps)
        ):
            elapsed_days = (today - state.last_advanced_date).days
            current_index = next(
                index for index, step in enumerate(steps) if step.id == current.id
            )
            current = steps[(current_index + elapsed_days) % len(steps)]
            state.current_step = current
            state.last_advanced_date = today
        while (
            current.step_type == ProgramStepType.REST.value
            and state.last_advanced_date < today
        ):
            current = self._next_step(steps, current)
            state.current_step = current
            state.last_advanced_date += timedelta(days=1)

        return DueProgramStep(
            program=program,
            step=current,
            last_advanced_date=state.last_advanced_date,
            is_started=True,
        )

    def get_due(self, user: User) -> DueProgramStep | None:
        due = self._resolve_due(user)
        # Reading can lazily consume elapsed rest days, so persist the resolved state.
        self.db.commit()
        return due

    def advance_after_workout(
        self,
        user: User,
        muscle_groups: set[str],
        *,
        template_id: uuid.UUID | None = None,
    ) -> bool:
        """Advance a due workout step without committing the surrounding transaction."""
        due = self._resolve_due(user)
        if (
            not due
            or not due.is_started
            or due.step.step_type != ProgramStepType.WORKOUT.value
        ):
            return False

        required_groups = set(due.step.muscle_groups or [])
        if due.program.advance_on_any_workout:
            matches = True
        elif due.step.linked_workout_template_id:
            matches = due.step.linked_workout_template_id == template_id
        else:
            matches = not required_groups or required_groups.issubset(muscle_groups)
        if not matches:
            return False

        steps = self._ordered_steps(due.program)
        due.program.cycle_state.current_step = self._next_step(steps, due.step)  # type: ignore[union-attr]
        due.program.cycle_state.last_advanced_date = local_today(user.timezone)  # type: ignore[union-attr]
        return True

    def manual_advance(
        self, user: User, *, target_step_id: uuid.UUID | None = None
    ) -> DueProgramStep:
        due = self._resolve_due(user)
        if not due:
            raise InputError("No active workout program")
        steps = self._ordered_steps(due.program)
        if target_step_id is None:
            target = self._next_step(steps, due.step)
        else:
            target = next((step for step in steps if step.id == target_step_id), None)
            if not target:
                raise InputError("Target step does not belong to the active program")

        state = due.program.cycle_state
        state.current_step = target  # type: ignore[union-attr]
        state.last_advanced_date = max(  # type: ignore[union-attr]
            local_today(user.timezone), due.program.starts_on
        )
        self.db.commit()
        return DueProgramStep(
            program=due.program,
            step=target,
            last_advanced_date=state.last_advanced_date,  # type: ignore[union-attr]
            is_started=local_today(user.timezone) >= due.program.starts_on,
        )
