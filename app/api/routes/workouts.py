import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.dependencies import CurrentUser, Database
from app.schemas.workout import WorkoutCreate, WorkoutPage, WorkoutRead, WorkoutUpdate
from app.services.workouts import WorkoutService

router = APIRouter(prefix="/workouts", tags=["workouts"])


@router.get("", response_model=WorkoutPage)
def list_workouts(
    user: CurrentUser,
    db: Database,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    date_from: date | None = None,
    date_to: date | None = None,
) -> WorkoutPage:
    workouts, total = WorkoutService(db).list_workouts(
        user,
        limit=limit,
        offset=offset,
        date_from=date_from,
        date_to=date_to,
    )
    return WorkoutPage(
        items=[WorkoutRead.from_model(item) for item in workouts],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{workout_id}", response_model=WorkoutRead)
def get_workout(workout_id: uuid.UUID, user: CurrentUser, db: Database) -> WorkoutRead:
    return WorkoutRead.from_model(WorkoutService(db).get(user, workout_id))


@router.post("", response_model=WorkoutRead, status_code=status.HTTP_201_CREATED)
def create_workout(data: WorkoutCreate, user: CurrentUser, db: Database) -> WorkoutRead:
    return WorkoutRead.from_model(WorkoutService(db).create(user, data))


@router.patch("/{workout_id}", response_model=WorkoutRead)
def update_workout(
    workout_id: uuid.UUID,
    data: WorkoutUpdate,
    user: CurrentUser,
    db: Database,
) -> WorkoutRead:
    return WorkoutRead.from_model(WorkoutService(db).update(user, workout_id, data))


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(workout_id: uuid.UUID, user: CurrentUser, db: Database) -> Response:
    WorkoutService(db).delete(user, workout_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
