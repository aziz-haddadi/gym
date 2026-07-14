import uuid

from fastapi import APIRouter, Query, Response, status

from app.api.dependencies import CurrentUser, Database
from app.schemas.machine import MachineCreate, MachineRead, MachineUpdate
from app.services.machines import MachineService

router = APIRouter(prefix="/machines", tags=["machines"])


@router.get("", response_model=list[MachineRead])
def list_machines(
    user: CurrentUser,
    db: Database,
    include_archived: bool = Query(default=False),
) -> list[MachineRead]:
    machines = MachineService(db).list_machines(user, include_archived)
    return [MachineRead.model_validate(machine) for machine in machines]


@router.post("", response_model=MachineRead, status_code=status.HTTP_201_CREATED)
def create_machine(data: MachineCreate, user: CurrentUser, db: Database) -> MachineRead:
    return MachineRead.model_validate(MachineService(db).create(user, data))


@router.patch("/{machine_id}", response_model=MachineRead)
def update_machine(
    machine_id: uuid.UUID,
    data: MachineUpdate,
    user: CurrentUser,
    db: Database,
) -> MachineRead:
    return MachineRead.model_validate(MachineService(db).update(user, machine_id, data))


@router.delete("/{machine_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_machine(machine_id: uuid.UUID, user: CurrentUser, db: Database) -> Response:
    MachineService(db).archive(user, machine_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
