"""
Shared date logic. "Today" in challenge terms means the most recent
FULLY COMPLETED day -- since you check a full day's screentime, you're
always reporting on yesterday, with a 4pm Singapore time deadline to do
so each day.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("Asia/Singapore")
DEADLINE_HOUR = 16  # 4:00 PM


def get_target_date_and_lock_status() -> tuple[date, bool]:
    now = datetime.now(TIMEZONE)
    target_date = (now - timedelta(days=1)).date()
    deadline_today = now.replace(hour=DEADLINE_HOUR, minute=0, second=0, microsecond=0)
    locked = now > deadline_today
    return target_date, locked