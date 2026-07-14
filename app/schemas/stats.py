import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class WeeklyStat(BaseModel):
    week_start: date
    workouts: int
    sets: int
    volume_kg: Decimal


class PersonalRecord(BaseModel):
    machine_id: uuid.UUID
    machine_name: str
    max_weight_kg: Decimal
    best_set_volume_kg: Decimal


class StatsOverview(BaseModel):
    current_streak: int
    longest_streak: int
    total_workouts: int
    workouts_last_30_days: int
    total_sets: int
    total_reps: int
    total_volume_kg: Decimal
    active_machines: int
    last_workout_date: date | None
    weekly: list[WeeklyStat]
    personal_records: list[PersonalRecord]
