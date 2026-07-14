import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.machine import Machine


class MachineRepository:
    """Persistence operations for a user's machine catalogue."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(self, user_id: uuid.UUID, include_archived: bool = False) -> list[Machine]:
        query = select(Machine).where(Machine.user_id == user_id)
        if not include_archived:
            query = query.where(Machine.active.is_(True))
        query = query.order_by(Machine.active.desc(), Machine.name.asc())
        return list(self.db.scalars(query))

    def get_for_user(self, machine_id: uuid.UUID, user_id: uuid.UUID) -> Machine | None:
        return self.db.scalar(
            select(Machine).where(Machine.id == machine_id, Machine.user_id == user_id)
        )

    def name_exists(
        self, user_id: uuid.UUID, name: str, exclude_id: uuid.UUID | None = None
    ) -> bool:
        query = (
            select(func.count())
            .select_from(Machine)
            .where(
                Machine.user_id == user_id,
                func.lower(Machine.name) == name.strip().lower(),
            )
        )
        if exclude_id:
            query = query.where(Machine.id != exclude_id)
        return bool(self.db.scalar(query))

    def add(self, machine: Machine) -> Machine:
        self.db.add(machine)
        self.db.flush()
        return machine
