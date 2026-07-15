"""Add rotating workout programs and stable cycle state.

Revision ID: 20260715_0005
Revises: 20260714_0004
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260715_0005"
down_revision: str | None = "20260714_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workout_programs",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column(
            "advance_on_any_workout",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "NOT is_active OR archived_at IS NULL",
            name=op.f("ck_workout_programs_active_program_not_archived"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_workout_programs_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workout_programs"),
    )
    op.create_index(
        "ix_workout_programs_user_id", "workout_programs", ["user_id"]
    )
    op.create_index(
        "ix_workout_programs_user_archived",
        "workout_programs",
        ["user_id", "archived_at"],
    )
    op.create_index(
        "uq_workout_programs_one_active_per_user",
        "workout_programs",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_active AND archived_at IS NULL"),
        sqlite_where=sa.text("is_active = 1 AND archived_at IS NULL"),
    )

    op.create_table(
        "workout_program_steps",
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("step_type", sa.String(length=16), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column("muscle_groups", sa.JSON(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "position >= 0",
            name=op.f("ck_workout_program_steps_position_nonnegative"),
        ),
        sa.CheckConstraint(
            "step_type IN ('workout', 'rest')",
            name=op.f("ck_workout_program_steps_step_type_allowed"),
        ),
        sa.CheckConstraint(
            "step_type = 'rest' OR (label IS NOT NULL AND length(trim(label)) > 0)",
            name=op.f("ck_workout_program_steps_workout_label_required"),
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["workout_programs.id"],
            name=op.f("fk_workout_program_steps_program_id_workout_programs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workout_program_steps"),
        sa.UniqueConstraint(
            "program_id",
            "position",
            name="uq_workout_program_steps_program_position",
        ),
    )
    op.create_index(
        "ix_workout_program_steps_program_id",
        "workout_program_steps",
        ["program_id"],
    )
    op.create_index(
        "ix_workout_program_steps_program_position",
        "workout_program_steps",
        ["program_id", "position"],
    )

    op.create_table(
        "workout_program_cycle_states",
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("current_step_id", sa.Uuid(), nullable=False),
        sa.Column("last_advanced_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["current_step_id"],
            ["workout_program_steps.id"],
            name=op.f("fk_program_cycle_current_step"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["workout_programs.id"],
            name=op.f(
                "fk_workout_program_cycle_states_program_id_workout_programs"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "program_id", name="pk_workout_program_cycle_states"
        ),
    )
    op.create_index(
        "ix_workout_program_cycle_states_current_step_id",
        "workout_program_cycle_states",
        ["current_step_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workout_program_cycle_states_current_step_id",
        table_name="workout_program_cycle_states",
    )
    op.drop_table("workout_program_cycle_states")
    op.drop_index(
        "ix_workout_program_steps_program_position",
        table_name="workout_program_steps",
    )
    op.drop_index(
        "ix_workout_program_steps_program_id",
        table_name="workout_program_steps",
    )
    op.drop_table("workout_program_steps")
    op.drop_index(
        "uq_workout_programs_one_active_per_user",
        table_name="workout_programs",
    )
    op.drop_index(
        "ix_workout_programs_user_archived", table_name="workout_programs"
    )
    op.drop_index("ix_workout_programs_user_id", table_name="workout_programs")
    op.drop_table("workout_programs")
