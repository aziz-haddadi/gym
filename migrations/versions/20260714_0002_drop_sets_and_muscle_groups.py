"""Add drop sets and use specific arm muscle groups.

Revision ID: 20260714_0002
Revises: 20260714_0001
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260714_0002"
down_revision: str | None = "20260714_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ALLOWED_MUSCLE_GROUPS = (
    "Chest",
    "Back",
    "Shoulders",
    "Biceps",
    "Triceps",
    "Forearms",
    "Legs",
    "Core",
    "Cardio",
    "Other",
)


def upgrade() -> None:
    op.add_column(
        "workout_sets",
        sa.Column("is_drop_set", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.alter_column("workout_sets", "is_drop_set", server_default=None)

    op.execute("UPDATE machines SET muscle_group = 'Biceps' WHERE muscle_group = 'Arms'")
    op.execute("UPDATE machines SET muscle_group = 'Other' WHERE muscle_group = 'Full Body'")
    allowed_values = ", ".join(f"'{value}'" for value in ALLOWED_MUSCLE_GROUPS)
    op.create_check_constraint(
        op.f("ck_machines_muscle_group_allowed"),
        "machines",
        f"muscle_group IN ({allowed_values})",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_machines_muscle_group_allowed"), "machines", type_="check")
    op.execute(
        "UPDATE machines SET muscle_group = 'Arms' "
        "WHERE muscle_group IN ('Biceps', 'Triceps', 'Forearms')"
    )
    op.drop_column("workout_sets", "is_drop_set")
