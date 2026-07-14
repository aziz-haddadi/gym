from typing import Annotated

from fastapi import APIRouter, Path, Response, status

from app.api.dependencies import CurrentUser, Database
from app.schemas.agenda import AgendaDayRead, AgendaDayWrite
from app.services.agenda import AgendaService

router = APIRouter(prefix="/agenda", tags=["agenda"])
Weekday = Annotated[int, Path(ge=0, le=6)]


@router.get("", response_model=list[AgendaDayRead])
def list_agenda(user: CurrentUser, db: Database) -> list[AgendaDayRead]:
    return [AgendaDayRead.model_validate(day) for day in AgendaService(db).list_days(user)]


@router.put("/{day_of_week}", response_model=AgendaDayRead)
def save_agenda_day(
    day_of_week: Weekday,
    data: AgendaDayWrite,
    user: CurrentUser,
    db: Database,
) -> AgendaDayRead:
    return AgendaDayRead.model_validate(AgendaService(db).save_day(user, day_of_week, data))


@router.delete("/{day_of_week}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agenda_day(day_of_week: Weekday, user: CurrentUser, db: Database) -> Response:
    AgendaService(db).delete_day(user, day_of_week)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
