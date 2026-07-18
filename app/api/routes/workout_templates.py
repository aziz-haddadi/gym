import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.dependencies import CurrentUser, Database
from app.schemas.workout_template import (
    WorkoutTemplateCreate,
    WorkoutTemplateExercisesUpdate,
    WorkoutTemplateRead,
    WorkoutTemplateUpdate,
)
from app.services.workout_templates import WorkoutTemplateService

router = APIRouter(prefix="/workout-templates", tags=["workout templates"])


@router.get("", response_model=list[WorkoutTemplateRead])
def list_workout_templates(
    user: CurrentUser,
    db: Database,
    include_archived: Annotated[bool, Query()] = False,
) -> list[WorkoutTemplateRead]:
    templates = WorkoutTemplateService(db).list_templates(
        user, include_archived=include_archived
    )
    return [WorkoutTemplateRead.from_model(item) for item in templates]


@router.post("", response_model=WorkoutTemplateRead, status_code=status.HTTP_201_CREATED)
def create_workout_template(
    data: WorkoutTemplateCreate, user: CurrentUser, db: Database
) -> WorkoutTemplateRead:
    return WorkoutTemplateRead.from_model(WorkoutTemplateService(db).create(user, data))


@router.get("/{template_id}", response_model=WorkoutTemplateRead)
def get_workout_template(
    template_id: uuid.UUID, user: CurrentUser, db: Database
) -> WorkoutTemplateRead:
    return WorkoutTemplateRead.from_model(WorkoutTemplateService(db).get(user, template_id))


@router.patch("/{template_id}", response_model=WorkoutTemplateRead)
def update_workout_template(
    template_id: uuid.UUID,
    data: WorkoutTemplateUpdate,
    user: CurrentUser,
    db: Database,
) -> WorkoutTemplateRead:
    return WorkoutTemplateRead.from_model(
        WorkoutTemplateService(db).update(user, template_id, data)
    )


@router.put("/{template_id}/exercises", response_model=WorkoutTemplateRead)
def update_workout_template_exercises(
    template_id: uuid.UUID,
    data: WorkoutTemplateExercisesUpdate,
    user: CurrentUser,
    db: Database,
) -> WorkoutTemplateRead:
    return WorkoutTemplateRead.from_model(
        WorkoutTemplateService(db).update_exercises(user, template_id, data)
    )


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_workout_template(
    template_id: uuid.UUID, user: CurrentUser, db: Database
) -> Response:
    WorkoutTemplateService(db).archive(user, template_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
