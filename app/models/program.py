from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workout_template import WorkoutTemplate


class WorkoutProgram(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workout_programs"
    __table_args__ = (
        CheckConstraint(
            "NOT is_active OR archived_at IS NULL",
            name="active_program_not_archived",
        ),
        Index("ix_workout_programs_user_archived", "user_id", "archived_at"),
        Index(
            "uq_workout_programs_one_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("is_active AND archived_at IS NULL"),
            sqlite_where=text("is_active = 1 AND archived_at IS NULL"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    advance_on_any_workout: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="programs")
    steps: Mapped[list[WorkoutProgramStep]] = relationship(
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="WorkoutProgramStep.position",
        foreign_keys="WorkoutProgramStep.program_id",
    )
    cycle_state: Mapped[WorkoutProgramCycleState | None] = relationship(
        back_populates="program",
        cascade="all, delete-orphan",
        uselist=False,
        foreign_keys="WorkoutProgramCycleState.program_id",
    )


class WorkoutProgramStep(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "workout_program_steps"
    __table_args__ = (
        CheckConstraint("position >= 0", name="position_nonnegative"),
        CheckConstraint(
            "step_type IN ('workout', 'rest')",
            name="step_type_allowed",
        ),
        CheckConstraint(
            "step_type = 'rest' OR (label IS NOT NULL AND length(trim(label)) > 0)",
            name="workout_label_required",
        ),
        UniqueConstraint(
            "program_id", "position", name="uq_workout_program_steps_program_position"
        ),
        Index("ix_workout_program_steps_program_position", "program_id", "position"),
    )

    program_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workout_programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[str] = mapped_column(String(16), nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    muscle_groups: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    linked_workout_template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "workout_templates.id",
            ondelete="SET NULL",
            name="fk_program_steps_linked_template",
        ),
        nullable=True,
        index=True,
    )

    program: Mapped[WorkoutProgram] = relationship(
        back_populates="steps", foreign_keys=[program_id]
    )
    current_for_states: Mapped[list[WorkoutProgramCycleState]] = relationship(
        back_populates="current_step",
        foreign_keys="WorkoutProgramCycleState.current_step_id",
    )
    linked_workout_template: Mapped[WorkoutTemplate | None] = relationship(
        back_populates="program_steps"
    )


class WorkoutProgramCycleState(TimestampMixin, Base):
    __tablename__ = "workout_program_cycle_states"

    program_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workout_programs.id", ondelete="CASCADE"), primary_key=True
    )
    current_step_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "workout_program_steps.id",
            ondelete="RESTRICT",
            name="fk_program_cycle_current_step",
        ),
        nullable=False,
        index=True,
    )
    last_advanced_date: Mapped[date] = mapped_column(Date, nullable=False)

    program: Mapped[WorkoutProgram] = relationship(
        back_populates="cycle_state", foreign_keys=[program_id]
    )
    current_step: Mapped[WorkoutProgramStep] = relationship(
        back_populates="current_for_states", foreign_keys=[current_step_id]
    )
