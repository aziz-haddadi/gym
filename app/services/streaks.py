from collections.abc import Iterable
from datetime import date, timedelta


def calculate_streaks(workout_dates: Iterable[date], today: date) -> tuple[int, int]:
    """Return current and longest daily workout streaks.

    A current streak remains alive during the day after the latest workout, which
    lets the user train later today without seeing yesterday's streak disappear.
    """

    days = sorted(set(workout_dates))
    if not days:
        return 0, 0

    longest = 1
    running = 1
    for previous, current in zip(days, days[1:], strict=False):
        if current == previous + timedelta(days=1):
            running += 1
            longest = max(longest, running)
        else:
            running = 1

    day_set = set(days)
    cursor = today if today in day_set else today - timedelta(days=1)
    if cursor not in day_set:
        return 0, longest

    current_streak = 0
    while cursor in day_set:
        current_streak += 1
        cursor -= timedelta(days=1)
    return current_streak, longest
