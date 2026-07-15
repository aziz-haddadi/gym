import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.models.program import WorkoutProgram, WorkoutProgramCycleState


class WorkoutProgramRepository:
    """User-scoped persistence operations for workout programs."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _with_graph(query: Select) -> Select:
        return query.options(
            selectinload(WorkoutProgram.steps),
            selectinload(WorkoutProgram.cycle_state).selectinload(
                WorkoutProgramCycleState.current_step
            ),
        )

    def list_for_user(
        self, user_id: uuid.UUID, *, include_archived: bool = False
    ) -> list[WorkoutProgram]:
        query = select(WorkoutProgram).where(WorkoutProgram.user_id == user_id)
        if not include_archived:
            query = query.where(WorkoutProgram.archived_at.is_(None))
        query = self._with_graph(
            query.order_by(WorkoutProgram.is_active.desc(), WorkoutProgram.created_at.desc())
        )
        return list(self.db.scalars(query))

    def get_for_user(
        self,
        program_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> WorkoutProgram | None:
        query = select(WorkoutProgram).where(
            WorkoutProgram.id == program_id,
            WorkoutProgram.user_id == user_id,
        )
        if for_update:
            query = query.with_for_update()
        return self.db.scalar(self._with_graph(query))

    def get_active_for_user(
        self, user_id: uuid.UUID, *, for_update: bool = False
    ) -> WorkoutProgram | None:
        query = select(WorkoutProgram).where(
            WorkoutProgram.user_id == user_id,
            WorkoutProgram.is_active.is_(True),
            WorkoutProgram.archived_at.is_(None),
        )
        if for_update:
            query = query.with_for_update()
        return self.db.scalar(self._with_graph(query))

    def lock_all_for_user(self, user_id: uuid.UUID) -> list[WorkoutProgram]:
        query = (
            select(WorkoutProgram)
            .where(WorkoutProgram.user_id == user_id)
            .order_by(WorkoutProgram.created_at, WorkoutProgram.id)
            .with_for_update()
        )
        return list(self.db.scalars(query))

    def add(self, program: WorkoutProgram) -> WorkoutProgram:
        self.db.add(program)
        self.db.flush()
        return program

    def refresh_graph(self, program: WorkoutProgram) -> WorkoutProgram:
        self.db.expire(program)
        refreshed = self.get_for_user(program.id, program.user_id)
        if refreshed is None:  # pragma: no cover - defensive invariant
            raise RuntimeError("Workout program disappeared during transaction")
        return refreshed
