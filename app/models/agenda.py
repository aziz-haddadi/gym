from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class AgendaDay(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agenda_days"
    __table_args__ = (
        UniqueConstraint("user_id", "day_of_week", name="uq_agenda_days_user_day"),
        CheckConstraint("day_of_week >= 0 AND day_of_week <= 6", name="day_of_week_range"),
        Index("ix_agenda_days_user_day", "user_id", "day_of_week"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    workout_name: Mapped[str] = mapped_column(String(100), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="agenda_days")
