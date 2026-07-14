from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.machine import Machine
    from app.models.user import User


class Workout(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workouts"
    __table_args__ = (Index("ix_workouts_user_date", "user_id", "workout_date"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workout_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(100), default="Workout", nullable=False)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="workouts")
    entries: Mapped[list[WorkoutEntry]] = relationship(
        back_populates="workout",
        cascade="all, delete-orphan",
        order_by="WorkoutEntry.position",
    )


class WorkoutEntry(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "workout_entries"
    __table_args__ = (
        CheckConstraint("position >= 0", name="position_nonnegative"),
        Index("ix_workout_entries_workout_position", "workout_id", "position"),
    )

    workout_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False
    )
    machine_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("machines.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    workout: Mapped[Workout] = relationship(back_populates="entries")
    machine: Mapped[Machine] = relationship(back_populates="workout_entries")
    sets: Mapped[list[WorkoutSet]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="WorkoutSet.set_number",
    )


class WorkoutSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "workout_sets"
    __table_args__ = (
        CheckConstraint("set_number > 0", name="set_number_positive"),
        CheckConstraint("reps > 0", name="reps_positive"),
        CheckConstraint("weight_kg >= 0", name="weight_nonnegative"),
        CheckConstraint("rpe IS NULL OR (rpe >= 1 AND rpe <= 10)", name="rpe_range"),
        Index("ix_workout_sets_entry_number", "entry_id", "set_number", unique=True),
    )

    entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workout_entries.id", ondelete="CASCADE"), nullable=False
    )
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    rpe: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    is_drop_set: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    entry: Mapped[WorkoutEntry] = relationship(back_populates="sets")
