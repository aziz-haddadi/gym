import uuid

from sqlalchemy.orm import Session

from app.models.machine import Machine
from app.models.user import User
from app.repositories.machines import MachineRepository
from app.schemas.machine import MachineCreate, MachineUpdate
from app.services.exceptions import ConflictError, NotFoundError


class MachineService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = MachineRepository(db)

    def list_machines(self, user: User, include_archived: bool = False) -> list[Machine]:
        return self.repository.list_for_user(user.id, include_archived)

    def create(self, user: User, data: MachineCreate) -> Machine:
        if self.repository.name_exists(user.id, data.name):
            raise ConflictError("A machine with this name already exists")
        machine = Machine(
            user_id=user.id,
            name=data.name,
            muscle_group=data.muscle_group.value,
            notes=data.notes,
        )
        self.repository.add(machine)
        self.db.commit()
        self.db.refresh(machine)
        return machine

    def update(self, user: User, machine_id: uuid.UUID, data: MachineUpdate) -> Machine:
        machine = self.repository.get_for_user(machine_id, user.id)
        if not machine:
            raise NotFoundError("Machine not found")
        changes = data.model_dump(exclude_unset=True)
        if "name" in changes and self.repository.name_exists(user.id, changes["name"], machine.id):
            raise ConflictError("A machine with this name already exists")
        if "muscle_group" in changes:
            changes["muscle_group"] = changes["muscle_group"].value
        for field, value in changes.items():
            setattr(machine, field, value)
        self.db.commit()
        self.db.refresh(machine)
        return machine

    def archive(self, user: User, machine_id: uuid.UUID) -> None:
        machine = self.repository.get_for_user(machine_id, user.id)
        if not machine:
            raise NotFoundError("Machine not found")
        machine.active = False
        self.db.commit()
