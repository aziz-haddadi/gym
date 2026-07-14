"""Remove the superseded manual weekly agenda.

Revision ID: 20260714_0004
Revises: 20260714_0003
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260714_0004"
down_revision: str | None = "20260714_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("agenda_days")


def downgrade() -> None:
    op.create_table(
        "agenda_days",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("workout_name", sa.String(length=100), nullable=False),
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
        sa.CheckConstraint(
            "day_of_week >= 0 AND day_of_week <= 6",
            name="day_of_week_range",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_agenda_days_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agenda_days"),
        sa.UniqueConstraint("user_id", "day_of_week", name="uq_agenda_days_user_day"),
    )
    op.create_index(
        "ix_agenda_days_user_day",
        "agenda_days",
        ["user_id", "day_of_week"],
    )
