from datetime import date

from app.services.streaks import calculate_streaks


def test_current_and_longest_streak_ending_today():
    dates = [date(2026, 7, 8), date(2026, 7, 10), date(2026, 7, 11), date(2026, 7, 12)]

    assert calculate_streaks(dates, date(2026, 7, 12)) == (3, 3)


def test_current_streak_survives_until_end_of_following_day():
    dates = [date(2026, 7, 10), date(2026, 7, 11), date(2026, 7, 12)]

    assert calculate_streaks(dates, date(2026, 7, 13)) == (3, 3)


def test_current_streak_expires_after_missed_day():
    dates = [date(2026, 7, 10), date(2026, 7, 11)]

    assert calculate_streaks(dates, date(2026, 7, 13)) == (0, 2)


def test_duplicate_days_do_not_inflate_streak():
    dates = [date(2026, 7, 11), date(2026, 7, 11), date(2026, 7, 12)]

    assert calculate_streaks(dates, date(2026, 7, 12)) == (2, 2)
