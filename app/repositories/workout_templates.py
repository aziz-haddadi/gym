import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.models.workout_template import WorkoutTemplate, WorkoutTemplateExercise


class WorkoutTemplateRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _with_graph(query: Select) -> Select:
        return query.options(
            selectinload(WorkoutTemplate.exercises).selectinload(
                WorkoutTemplateExercise.machine
            )
        )

    def list_for_user(
        self, user_id: uuid.UUID, *, include_archived: bool = False
    ) -> list[WorkoutTemplate]:
        query = select(WorkoutTemplate).where(WorkoutTemplate.user_id == user_id)
        if not include_archived:
            query = query.where(WorkoutTemplate.archived_at.is_(None))
        query = self._with_graph(query.order_by(WorkoutTemplate.name))
        return list(self.db.scalars(query))

    def get_for_user(
        self,
        template_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> WorkoutTemplate | None:
        query = select(WorkoutTemplate).where(
            WorkoutTemplate.id == template_id,
            WorkoutTemplate.user_id == user_id,
        )
        if for_update:
            query = query.with_for_update()
        return self.db.scalar(self._with_graph(query))

    def get_by_name(self, user_id: uuid.UUID, name: str) -> WorkoutTemplate | None:
        return self.db.scalar(
            select(WorkoutTemplate).where(
                WorkoutTemplate.user_id == user_id,
                WorkoutTemplate.name == name,
            )
        )

    def refresh_graph(self, template: WorkoutTemplate) -> WorkoutTemplate:
        self.db.expire(template)
        refreshed = self.get_for_user(template.id, template.user_id)
        if not refreshed:  # pragma: no cover
            raise RuntimeError("Saved workout disappeared during transaction")
        return refreshed
