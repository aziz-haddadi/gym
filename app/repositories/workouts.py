import uuid
from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.workout import Workout, WorkoutEntry


class WorkoutRepository:
    """Persistence operations for workouts and their set graph."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _with_graph(query: Select) -> Select:
        return query.options(
            selectinload(Workout.template),
            selectinload(Workout.entries).selectinload(WorkoutEntry.machine),
            selectinload(Workout.entries).selectinload(WorkoutEntry.sets),
        )

    def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        offset: int,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[Workout], int]:
        filters = [Workout.user_id == user_id]
        if date_from:
            filters.append(Workout.workout_date >= date_from)
        if date_to:
            filters.append(Workout.workout_date <= date_to)

        count = self.db.scalar(select(func.count()).select_from(Workout).where(*filters)) or 0
        query = self._with_graph(
            select(Workout)
            .where(*filters)
            .order_by(Workout.workout_date.desc(), Workout.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(query)), count

    def get_for_user(self, workout_id: uuid.UUID, user_id: uuid.UUID) -> Workout | None:
        query = self._with_graph(
            select(Workout).where(Workout.id == workout_id, Workout.user_id == user_id)
        )
        return self.db.scalar(query)

    def add(self, workout: Workout) -> Workout:
        self.db.add(workout)
        self.db.flush()
        return workout

    def refresh_graph(self, workout: Workout) -> Workout:
        self.db.expire(workout, ["entries"])
        refreshed = self.get_for_user(workout.id, workout.user_id)
        if refreshed is None:  # pragma: no cover - defensive invariant
            raise RuntimeError("Workout disappeared during transaction")
        return refreshed
