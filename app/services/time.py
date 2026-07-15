from datetime import date, datetime
from zoneinfo import ZoneInfo


def local_today(timezone_name: str) -> date:
    """Return today's date in a user's configured timezone."""
    try:
        return datetime.now(ZoneInfo(timezone_name)).date()
    except (KeyError, ValueError):  # pragma: no cover - user creation validates zones
        return date.today()
