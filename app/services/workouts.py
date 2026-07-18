import uuid

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.workout import Workout, WorkoutEntry, WorkoutSet
from app.repositories.machines import MachineRepository
from app.repositories.workouts import WorkoutRepository
from app.schemas.workout import WorkoutCreate, WorkoutEntryWrite, WorkoutUpdate
from app.services.exceptions import InputError, NotFoundError
from app.services.programs import WorkoutProgramService
from app.services.workout_templates import WorkoutTemplateService


class WorkoutService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = WorkoutRepository(db)
        self.machines = MachineRepository(db)
        self.templates = WorkoutTemplateService(db)

    def list_workouts(self, user: User, **filters) -> tuple[list[Workout], int]:
        return self.repository.list_for_user(user.id, **filters)

    def get(self, user: User, workout_id: uuid.UUID) -> Workout:
        workout = self.repository.get_for_user(workout_id, user.id)
        if not workout:
            raise NotFoundError("Workout not found")
        return workout

    def _build_entries(
        self, user: User, entries: list[WorkoutEntryWrite]
    ) -> tuple[list[WorkoutEntry], set[str]]:
        result: list[WorkoutEntry] = []
        muscle_groups: set[str] = set()
        for position, entry_data in enumerate(entries):
            machine = self.machines.get_for_user(entry_data.machine_id, user.id)
            if not machine:
                raise InputError("One of the selected machines does not exist")
            if not machine.active:
                raise InputError(f"{machine.name} is archived and cannot be added")
            muscle_groups.add(machine.muscle_group)
            entry = WorkoutEntry(
                machine_id=machine.id,
                position=position,
                notes=entry_data.notes,
            )
            entry.sets = [
                WorkoutSet(
                    set_number=index,
                    reps=item.reps,
                    weight_kg=item.weight_kg,
                    rpe=item.rpe,
                    is_drop_set=item.is_drop_set,
                )
                for index, item in enumerate(entry_data.sets, start=1)
            ]
            result.append(entry)
        return result, muscle_groups

    def create(self, user: User, data: WorkoutCreate) -> Workout:
        template = (
            self.templates.get_loggable(user, data.template_id) if data.template_id else None
        )
        entries, muscle_groups = self._build_entries(user, data.entries)
        workout = Workout(
            user_id=user.id,
            template_id=template.id if template else None,
            workout_date=data.workout_date,
            title=data.title,
            duration_minutes=data.duration_minutes,
            notes=data.notes,
            entries=entries,
        )
        self.repository.add(workout)
        WorkoutProgramService(self.db).advance_after_workout(
            user,
            muscle_groups,
            template_id=template.id if template else None,
        )
        self.db.commit()
        return self.repository.get_for_user(workout.id, user.id)  # type: ignore[return-value]

    def update(self, user: User, workout_id: uuid.UUID, data: WorkoutUpdate) -> Workout:
        workout = self.get(user, workout_id)
        changes = data.model_dump(exclude_unset=True, exclude={"entries"})
        for field, value in changes.items():
            setattr(workout, field, value)
        if data.entries is not None:
            workout.entries.clear()
            self.db.flush()
            workout.entries = self._build_entries(user, data.entries)[0]
        self.db.commit()
        return self.repository.get_for_user(workout.id, user.id)  # type: ignore[return-value]

    def delete(self, user: User, workout_id: uuid.UUID) -> None:
        workout = self.get(user, workout_id)
        self.db.delete(workout)
        self.db.commit()
