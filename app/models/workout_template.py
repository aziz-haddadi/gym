from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.machine import Machine
    from app.models.program import WorkoutProgramStep
    from app.models.user import User
    from app.models.workout import Workout


class WorkoutTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workout_templates"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_workout_templates_user_name"),
        Index("ix_workout_templates_user_archived", "user_id", "archived_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="workout_templates")
    exercises: Mapped[list[WorkoutTemplateExercise]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="WorkoutTemplateExercise.position",
    )
    logged_workouts: Mapped[list[Workout]] = relationship(back_populates="template")
    program_steps: Mapped[list[WorkoutProgramStep]] = relationship(
        back_populates="linked_workout_template"
    )


class WorkoutTemplateExercise(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "workout_template_exercises"
    __table_args__ = (
        CheckConstraint("position >= 0", name="position_nonnegative"),
        UniqueConstraint(
            "template_id", "position", name="uq_workout_template_exercises_position"
        ),
        UniqueConstraint(
            "template_id", "machine_id", name="uq_workout_template_exercises_machine"
        ),
        Index("ix_workout_template_exercises_template_position", "template_id", "position"),
    )

    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "workout_templates.id",
            ondelete="CASCADE",
            name="fk_template_exercises_template",
        ),
        nullable=False,
        index=True,
    )
    machine_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("machines.id", ondelete="RESTRICT", name="fk_template_exercises_machine"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    template: Mapped[WorkoutTemplate] = relationship(back_populates="exercises")
    machine: Mapped[Machine] = relationship(back_populates="template_exercises")
