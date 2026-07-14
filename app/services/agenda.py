from sqlalchemy.orm import Session

from app.models.agenda import AgendaDay
from app.models.user import User
from app.repositories.agenda import AgendaRepository
from app.schemas.agenda import AgendaDayWrite
from app.services.exceptions import NotFoundError


class AgendaService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AgendaRepository(db)

    def list_days(self, user: User) -> list[AgendaDay]:
        return self.repository.list_for_user(user.id)

    def save_day(self, user: User, day_of_week: int, data: AgendaDayWrite) -> AgendaDay:
        agenda_day = self.repository.get_for_user(user.id, day_of_week)
        if agenda_day is None:
            agenda_day = self.repository.add(
                AgendaDay(
                    user_id=user.id,
                    day_of_week=day_of_week,
                    workout_name=data.workout_name,
                    notes=data.notes,
                )
            )
        else:
            agenda_day.workout_name = data.workout_name
            agenda_day.notes = data.notes
        self.db.commit()
        self.db.refresh(agenda_day)
        return agenda_day

    def delete_day(self, user: User, day_of_week: int) -> None:
        agenda_day = self.repository.get_for_user(user.id, day_of_week)
        if agenda_day is None:
            raise NotFoundError("Agenda day not found")
        self.db.delete(agenda_day)
        self.db.commit()
