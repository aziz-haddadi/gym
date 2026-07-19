"""Assign every program step to its own calendar date.

Revision ID: 20260719_0007
Revises: 20260718_0006
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260719_0007"
down_revision: str | None = "20260718_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workout_program_cycle_states",
        sa.Column("due_date", sa.Date(), nullable=True),
    )
    # Under the previous behavior, a workout moved the pointer immediately and
    # stored that workout date in last_advanced_date. Put that newly selected
    # step on the following day. States without a workout on the advancement
    # date keep their existing date (activation or lazy rest advancement).
    op.execute(
        sa.text(
            """
            UPDATE workout_program_cycle_states AS state
            SET due_date = GREATEST(
                program.starts_on,
                state.last_advanced_date + CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM workouts AS workout
                        WHERE workout.user_id = program.user_id
                          AND workout.workout_date = state.last_advanced_date
                    ) THEN 1
                    ELSE 0
                END
            )
            FROM workout_programs AS program
            WHERE program.id = state.program_id
            """
        )
    )
    op.alter_column(
        "workout_program_cycle_states",
        "due_date",
        existing_type=sa.Date(),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("workout_program_cycle_states", "due_date")
