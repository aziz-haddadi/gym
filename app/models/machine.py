from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.muscles import MUSCLE_GROUP_VALUES
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workout import WorkoutEntry

MUSCLE_GROUP_SQL_VALUES = ", ".join(f"'{value}'" for value in MUSCLE_GROUP_VALUES)


class Machine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "machines"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_machines_user_name"),
        CheckConstraint(
            f"muscle_group IN ({MUSCLE_GROUP_SQL_VALUES})",
            name="muscle_group_allowed",
        ),
        Index("ix_machines_user_active", "user_id", "active"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    muscle_group: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped[User] = relationship(back_populates="machines")
    workout_entries: Mapped[list[WorkoutEntry]] = relationship(back_populates="machine")
