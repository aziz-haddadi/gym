import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.dependencies import CurrentUser, Database
from app.schemas.program import (
    ProgramAdvanceRequest,
    ProgramCreate,
    ProgramDueRead,
    ProgramRead,
    ProgramStepsUpdate,
    ProgramUpdate,
)
from app.services.programs import DueProgramStep, WorkoutProgramService

router = APIRouter(prefix="/programs", tags=["programs"])


def due_response(due: DueProgramStep | None) -> ProgramDueRead | None:
    if due is None:
        return None
    return ProgramDueRead.from_models(
        due.program,
        due.step,
        due.last_advanced_date,
    )


@router.get("/active/due", response_model=ProgramDueRead | None)
def get_due_program_step(user: CurrentUser, db: Database) -> ProgramDueRead | None:
    return due_response(WorkoutProgramService(db).get_due(user))


@router.post("/active/advance", response_model=ProgramDueRead)
def manually_advance_program(
    data: ProgramAdvanceRequest,
    user: CurrentUser,
    db: Database,
) -> ProgramDueRead:
    due = WorkoutProgramService(db).manual_advance(
        user, target_step_id=data.target_step_id
    )
    return due_response(due)  # type: ignore[return-value]


@router.get("", response_model=list[ProgramRead])
def list_programs(
    user: CurrentUser,
    db: Database,
    include_archived: Annotated[bool, Query()] = False,
) -> list[ProgramRead]:
    programs = WorkoutProgramService(db).list_programs(
        user, include_archived=include_archived
    )
    return [ProgramRead.from_model(program) for program in programs]


@router.post("", response_model=ProgramRead, status_code=status.HTTP_201_CREATED)
def create_program(
    data: ProgramCreate, user: CurrentUser, db: Database
) -> ProgramRead:
    return ProgramRead.from_model(WorkoutProgramService(db).create(user, data))


@router.get("/{program_id}", response_model=ProgramRead)
def get_program(
    program_id: uuid.UUID, user: CurrentUser, db: Database
) -> ProgramRead:
    return ProgramRead.from_model(WorkoutProgramService(db).get(user, program_id))


@router.patch("/{program_id}", response_model=ProgramRead)
def update_program(
    program_id: uuid.UUID,
    data: ProgramUpdate,
    user: CurrentUser,
    db: Database,
) -> ProgramRead:
    return ProgramRead.from_model(
        WorkoutProgramService(db).update(user, program_id, data)
    )


@router.put("/{program_id}/steps", response_model=ProgramRead)
def update_program_steps(
    program_id: uuid.UUID,
    data: ProgramStepsUpdate,
    user: CurrentUser,
    db: Database,
) -> ProgramRead:
    return ProgramRead.from_model(
        WorkoutProgramService(db).update_steps(user, program_id, data)
    )


@router.post("/{program_id}/activate", response_model=ProgramRead)
def activate_program(
    program_id: uuid.UUID, user: CurrentUser, db: Database
) -> ProgramRead:
    return ProgramRead.from_model(
        WorkoutProgramService(db).activate(user, program_id)
    )


@router.delete("/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_program(
    program_id: uuid.UUID, user: CurrentUser, db: Database
) -> Response:
    WorkoutProgramService(db).archive(user, program_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
