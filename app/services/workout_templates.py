import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.base import utc_now
from app.models.user import User
from app.models.workout_template import WorkoutTemplate, WorkoutTemplateExercise
from app.repositories.machines import MachineRepository
from app.repositories.workout_templates import WorkoutTemplateRepository
from app.schemas.workout_template import (
    WorkoutTemplateCreate,
    WorkoutTemplateExercisesUpdate,
    WorkoutTemplateExerciseWrite,
    WorkoutTemplateUpdate,
)
from app.services.exceptions import ConflictError, InputError, NotFoundError


class WorkoutTemplateService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = WorkoutTemplateRepository(db)
        self.machines = MachineRepository(db)

    def list_templates(
        self, user: User, *, include_archived: bool = False
    ) -> list[WorkoutTemplate]:
        return self.repository.list_for_user(user.id, include_archived=include_archived)

    def get(self, user: User, template_id: uuid.UUID) -> WorkoutTemplate:
        template = self.repository.get_for_user(template_id, user.id)
        if not template:
            raise NotFoundError("Saved workout not found")
        return template

    def get_loggable(self, user: User, template_id: uuid.UUID) -> WorkoutTemplate:
        template = self.get(user, template_id)
        self._assert_editable(template)
        return template

    @staticmethod
    def _assert_editable(template: WorkoutTemplate) -> None:
        if template.archived_at is not None:
            raise InputError("Archived workouts cannot be edited or logged")

    def _exercise_model(
        self,
        user: User,
        template_id: uuid.UUID,
        position: int,
        data: WorkoutTemplateExerciseWrite,
    ) -> WorkoutTemplateExercise:
        machine = self.machines.get_for_user(data.machine_id, user.id)
        if not machine:
            raise InputError("One of the selected exercises does not exist")
        if not machine.active:
            raise InputError(f"{machine.name} is archived and cannot be added")
        return WorkoutTemplateExercise(
            template_id=template_id,
            machine_id=machine.id,
            position=position,
            notes=data.notes,
        )

    def _commit(self, duplicate_message: str) -> None:
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError(duplicate_message) from exc

    def create(self, user: User, data: WorkoutTemplateCreate) -> WorkoutTemplate:
        if self.repository.get_by_name(user.id, data.name):
            raise ConflictError("A saved workout with this name already exists")
        template = WorkoutTemplate(user_id=user.id, name=data.name, notes=data.notes)
        self.db.add(template)
        self.db.flush()
        template.exercises = [
            self._exercise_model(user, template.id, position, item)
            for position, item in enumerate(data.exercises)
        ]
        self._commit("A saved workout with this name or exercise already exists")
        return self.repository.refresh_graph(template)

    def update(
        self, user: User, template_id: uuid.UUID, data: WorkoutTemplateUpdate
    ) -> WorkoutTemplate:
        template = self.repository.get_for_user(template_id, user.id, for_update=True)
        if not template:
            raise NotFoundError("Saved workout not found")
        self._assert_editable(template)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(template, field, value)
        self._commit("A saved workout with this name already exists")
        return self.repository.refresh_graph(template)

    def update_exercises(
        self,
        user: User,
        template_id: uuid.UUID,
        data: WorkoutTemplateExercisesUpdate,
    ) -> WorkoutTemplate:
        template = self.repository.get_for_user(template_id, user.id, for_update=True)
        if not template:
            raise NotFoundError("Saved workout not found")
        self._assert_editable(template)
        old_exercises = sorted(template.exercises, key=lambda item: item.position)
        old_by_id = {item.id: item for item in old_exercises}
        incoming_ids = {item.id for item in data.exercises if item.id is not None}
        if incoming_ids.difference(old_by_id):
            raise InputError("One or more exercises do not belong to this saved workout")

        for offset, exercise in enumerate(old_exercises, start=1000):
            exercise.position = offset
        self.db.flush()

        new_exercises: list[WorkoutTemplateExercise] = []
        for position, item in enumerate(data.exercises):
            machine = self.machines.get_for_user(item.machine_id, user.id)
            if not machine or not machine.active:
                raise InputError("One of the selected exercises is unavailable")
            exercise = (
                old_by_id[item.id]
                if item.id is not None
                else WorkoutTemplateExercise(template_id=template.id)
            )
            exercise.machine_id = machine.id
            exercise.position = position
            exercise.notes = item.notes
            new_exercises.append(exercise)
        template.exercises = new_exercises
        self._commit("An exercise can appear only once in a saved workout")
        return self.repository.refresh_graph(template)

    def archive(self, user: User, template_id: uuid.UUID) -> None:
        template = self.repository.get_for_user(template_id, user.id, for_update=True)
        if not template:
            raise NotFoundError("Saved workout not found")
        if template.archived_at is None:
            template.archived_at = utc_now()
            self.db.commit()
