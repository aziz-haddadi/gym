from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.models.machine import Machine
from app.models.user import User
from app.models.workout import Workout, WorkoutEntry, WorkoutSet
from app.schemas.stats import PersonalRecord, StatsOverview, WeeklyStat
from app.services.streaks import calculate_streaks


class StatsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def overview(self, user: User) -> StatsOverview:
        today = date.today()
        try:
            today = datetime.now(ZoneInfo(user.timezone)).date()
        except Exception:  # pragma: no cover - invalid zones are rejected when users are created
            pass

        workout_dates = list(
            self.db.scalars(
                select(distinct(Workout.workout_date))
                .where(Workout.user_id == user.id)
                .order_by(Workout.workout_date)
            )
        )
        current_streak, longest_streak = calculate_streaks(workout_dates, today)
        total_workouts = (
            self.db.scalar(
                select(func.count()).select_from(Workout).where(Workout.user_id == user.id)
            )
            or 0
        )
        last_workout_date = workout_dates[-1] if workout_dates else None
        thirty_days_ago = today - timedelta(days=29)
        workouts_last_30_days = (
            self.db.scalar(
                select(func.count())
                .select_from(Workout)
                .where(
                    Workout.user_id == user.id,
                    Workout.workout_date >= thirty_days_ago,
                    Workout.workout_date <= today,
                )
            )
            or 0
        )

        totals = self.db.execute(
            select(
                func.count(WorkoutSet.id),
                func.coalesce(func.sum(WorkoutSet.reps), 0),
                func.coalesce(func.sum(WorkoutSet.weight_kg * WorkoutSet.reps), 0),
            )
            .select_from(WorkoutSet)
            .join(WorkoutEntry, WorkoutSet.entry_id == WorkoutEntry.id)
            .join(Workout, WorkoutEntry.workout_id == Workout.id)
            .where(Workout.user_id == user.id)
        ).one()

        active_machines = (
            self.db.scalar(
                select(func.count())
                .select_from(Machine)
                .where(Machine.user_id == user.id, Machine.active.is_(True))
            )
            or 0
        )

        week_start = today - timedelta(days=today.weekday())
        first_week = week_start - timedelta(weeks=11)
        set_rows = self.db.execute(
            select(Workout.workout_date, Workout.id, WorkoutSet.reps, WorkoutSet.weight_kg)
            .select_from(Workout)
            .outerjoin(WorkoutEntry, WorkoutEntry.workout_id == Workout.id)
            .outerjoin(WorkoutSet, WorkoutSet.entry_id == WorkoutEntry.id)
            .where(Workout.user_id == user.id, Workout.workout_date >= first_week)
        ).all()
        weekly_data: dict[date, dict] = defaultdict(
            lambda: {"workout_ids": set(), "sets": 0, "volume": Decimal("0")}
        )
        for workout_date, workout_id, reps, weight in set_rows:
            key = workout_date - timedelta(days=workout_date.weekday())
            weekly_data[key]["workout_ids"].add(workout_id)
            if reps is not None and weight is not None:
                weekly_data[key]["sets"] += 1
                weekly_data[key]["volume"] += weight * reps
        weekly = []
        for index in range(12):
            key = first_week + timedelta(weeks=index)
            values = weekly_data[key]
            weekly.append(
                WeeklyStat(
                    week_start=key,
                    workouts=len(values["workout_ids"]),
                    sets=values["sets"],
                    volume_kg=values["volume"],
                )
            )

        record_rows = self.db.execute(
            select(
                Machine.id,
                Machine.name,
                func.max(WorkoutSet.weight_kg),
                func.max(WorkoutSet.weight_kg * WorkoutSet.reps),
            )
            .select_from(Machine)
            .join(WorkoutEntry, WorkoutEntry.machine_id == Machine.id)
            .join(WorkoutSet, WorkoutSet.entry_id == WorkoutEntry.id)
            .join(Workout, Workout.id == WorkoutEntry.workout_id)
            .where(Workout.user_id == user.id)
            .group_by(Machine.id, Machine.name)
            .order_by(func.max(WorkoutSet.weight_kg).desc())
            .limit(12)
        ).all()
        records = [
            PersonalRecord(
                machine_id=machine_id,
                machine_name=name,
                max_weight_kg=max_weight,
                best_set_volume_kg=best_volume,
            )
            for machine_id, name, max_weight, best_volume in record_rows
        ]

        return StatsOverview(
            current_streak=current_streak,
            longest_streak=longest_streak,
            total_workouts=total_workouts,
            workouts_last_30_days=workouts_last_30_days,
            total_sets=totals[0],
            total_reps=totals[1],
            total_volume_kg=totals[2],
            active_machines=active_machines,
            last_workout_date=last_workout_date,
            weekly=weekly,
            personal_records=records,
        )
