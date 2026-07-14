"""Create users, sessions, machines, workouts, entries, and sets.

Revision ID: 20260714_0001
Revises:
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260714_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "auth_sessions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_auth_sessions_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_auth_sessions"),
        sa.UniqueConstraint("token_hash", name="uq_auth_sessions_token_hash"),
    )
    op.create_index("ix_auth_sessions_expiry", "auth_sessions", ["expires_at"])
    op.create_index("ix_auth_sessions_token_hash", "auth_sessions", ["token_hash"], unique=True)
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])

    op.create_table(
        "machines",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("muscle_group", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
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
            ["user_id"], ["users.id"], name="fk_machines_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_machines"),
        sa.UniqueConstraint("user_id", "name", name="uq_machines_user_name"),
    )
    op.create_index("ix_machines_user_active", "machines", ["user_id", "active"])
    op.create_index("ix_machines_user_id", "machines", ["user_id"])

    op.create_table(
        "workouts",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("workout_date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
            ["user_id"], ["users.id"], name="fk_workouts_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workouts"),
    )
    op.create_index("ix_workouts_user_date", "workouts", ["user_id", "workout_date"])
    op.create_index("ix_workouts_user_id", "workouts", ["user_id"])
    op.create_index("ix_workouts_workout_date", "workouts", ["workout_date"])

    op.create_table(
        "workout_entries",
        sa.Column("workout_id", sa.Uuid(), nullable=False),
        sa.Column("machine_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_workout_entries_position_nonnegative"),
        sa.ForeignKeyConstraint(
            ["machine_id"],
            ["machines.id"],
            name="fk_workout_entries_machine_id_machines",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["workout_id"],
            ["workouts.id"],
            name="fk_workout_entries_workout_id_workouts",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workout_entries"),
    )
    op.create_index("ix_workout_entries_machine_id", "workout_entries", ["machine_id"])
    op.create_index(
        "ix_workout_entries_workout_position", "workout_entries", ["workout_id", "position"]
    )

    op.create_table(
        "workout_sets",
        sa.Column("entry_id", sa.Uuid(), nullable=False),
        sa.Column("set_number", sa.Integer(), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=False),
        sa.Column("weight_kg", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("rpe", sa.Numeric(precision=3, scale=1), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "rpe IS NULL OR (rpe >= 1 AND rpe <= 10)", name="ck_workout_sets_rpe_range"
        ),
        sa.CheckConstraint("reps > 0", name="ck_workout_sets_reps_positive"),
        sa.CheckConstraint("set_number > 0", name="ck_workout_sets_set_number_positive"),
        sa.CheckConstraint("weight_kg >= 0", name="ck_workout_sets_weight_nonnegative"),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["workout_entries.id"],
            name="fk_workout_sets_entry_id_workout_entries",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workout_sets"),
    )
    op.create_index(
        "ix_workout_sets_entry_number", "workout_sets", ["entry_id", "set_number"], unique=True
    )


def downgrade() -> None:
    op.drop_table("workout_sets")
    op.drop_table("workout_entries")
    op.drop_table("workouts")
    op.drop_table("machines")
    op.drop_table("auth_sessions")
    op.drop_table("users")
