"""
The main leaderboard page -- the app's landing screen. Three tabs:
Today, This Week (so far), Total Competition (so far).
"""

from datetime import timedelta

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from db.connection import get_db
from db.models import Profile
from routes.auth import get_current_user
from logic.dates import get_target_date_and_lock_status
from logic.leaderboard import build_daily_table, build_range_table, get_challenge_start_date

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def leaderboard(
    request: Request,
    tab: str = "today",
    current_user: Profile | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    target_date, _ = get_target_date_and_lock_status()
    challenge_start = get_challenge_start_date(db)

    CHALLENGE_LENGTH_DAYS = 100
    day_number = (target_date - challenge_start).days + 1
    day_number = max(day_number, 1)  # never show below Day 1
    progress_percent = min(round((day_number / CHALLENGE_LENGTH_DAYS) * 100), 100)

    if tab == "week":
        week_start = target_date - timedelta(days=target_date.isoweekday() - 1)
        week_start = max(week_start, challenge_start)
        rows = build_range_table(db, week_start, target_date)
    elif tab == "total":
        rows = build_range_table(db, challenge_start, target_date)
    else:
        tab = "today"
        rows = build_daily_table(db, target_date)

    return templates.TemplateResponse(
        request=request,
        name="leaderboard.html",
        context={
            "rows": rows,
            "active_tab": tab,
            "current_user": current_user,
            "target_date": target_date,
            "day_number": day_number,
            "challenge_length": CHALLENGE_LENGTH_DAYS,
            "progress_percent": progress_percent,
        },
    )