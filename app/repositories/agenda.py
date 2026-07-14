import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agenda import AgendaDay


class AgendaRepository:
    """Persistence operations for a user's weekly training agenda."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(self, user_id: uuid.UUID) -> list[AgendaDay]:
        return list(
            self.db.scalars(
                select(AgendaDay)
                .where(AgendaDay.user_id == user_id)
                .order_by(AgendaDay.day_of_week)
            )
        )

    def get_for_user(self, user_id: uuid.UUID, day_of_week: int) -> AgendaDay | None:
        return self.db.scalar(
            select(AgendaDay).where(
                AgendaDay.user_id == user_id,
                AgendaDay.day_of_week == day_of_week,
            )
        )

    def add(self, agenda_day: AgendaDay) -> AgendaDay:
        self.db.add(agenda_day)
        self.db.flush()
        return agenda_day
