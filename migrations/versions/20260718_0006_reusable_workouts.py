"""Add reusable workouts and program start dates.

Revision ID: 20260718_0006
Revises: 20260715_0005
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260718_0006"
down_revision: str | None = "20260715_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workout_templates",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_workout_templates_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workout_templates")),
        sa.UniqueConstraint(
            "user_id", "name", name=op.f("uq_workout_templates_user_name")
        ),
    )
    op.create_index(
        "ix_workout_templates_user_id", "workout_templates", ["user_id"]
    )
    op.create_index(
        "ix_workout_templates_user_archived",
        "workout_templates",
        ["user_id", "archived_at"],
    )

    op.create_table(
        "workout_template_exercises",
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("machine_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "position >= 0",
            name=op.f("ck_workout_template_exercises_position_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["workout_templates.id"],
            name=op.f("fk_template_exercises_template"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["machine_id"],
            ["machines.id"],
            name=op.f("fk_template_exercises_machine"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workout_template_exercises")),
        sa.UniqueConstraint(
            "template_id",
            "machine_id",
            name=op.f("uq_workout_template_exercises_machine"),
        ),
        sa.UniqueConstraint(
            "template_id",
            "position",
            name=op.f("uq_workout_template_exercises_position"),
        ),
    )
    op.create_index(
        "ix_workout_template_exercises_template_id",
        "workout_template_exercises",
        ["template_id"],
    )
    op.create_index(
        "ix_workout_template_exercises_machine_id",
        "workout_template_exercises",
        ["machine_id"],
    )
    op.create_index(
        "ix_workout_template_exercises_template_position",
        "workout_template_exercises",
        ["template_id", "position"],
    )

    op.add_column(
        "workout_programs",
        sa.Column(
            "starts_on",
            sa.Date(),
            server_default=sa.text("CURRENT_DATE"),
            nullable=False,
        ),
    )
    op.add_column(
        "workout_program_steps",
        sa.Column("linked_workout_template_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_program_steps_linked_template"),
        "workout_program_steps",
        "workout_templates",
        ["linked_workout_template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_workout_program_steps_linked_workout_template_id",
        "workout_program_steps",
        ["linked_workout_template_id"],
    )

    op.add_column("workouts", sa.Column("template_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_workouts_template"),
        "workouts",
        "workout_templates",
        ["template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_workouts_template_id", "workouts", ["template_id"])


def downgrade() -> None:
    op.drop_index("ix_workouts_template_id", table_name="workouts")
    op.drop_constraint(
        op.f("fk_workouts_template"), "workouts", type_="foreignkey"
    )
    op.drop_column("workouts", "template_id")

    op.drop_index(
        "ix_workout_program_steps_linked_workout_template_id",
        table_name="workout_program_steps",
    )
    op.drop_constraint(
        op.f("fk_program_steps_linked_template"),
        "workout_program_steps",
        type_="foreignkey",
    )
    op.drop_column("workout_program_steps", "linked_workout_template_id")
    op.drop_column("workout_programs", "starts_on")

    op.drop_index(
        "ix_workout_template_exercises_template_position",
        table_name="workout_template_exercises",
    )
    op.drop_index(
        "ix_workout_template_exercises_machine_id",
        table_name="workout_template_exercises",
    )
    op.drop_index(
        "ix_workout_template_exercises_template_id",
        table_name="workout_template_exercises",
    )
    op.drop_table("workout_template_exercises")
    op.drop_index(
        "ix_workout_templates_user_archived", table_name="workout_templates"
    )
    op.drop_index("ix_workout_templates_user_id", table_name="workout_templates")
    op.drop_table("workout_templates")
