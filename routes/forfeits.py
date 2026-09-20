"""
The Forfeits page: shows weekly loser history and the final 100-day
forfeit. Admin can record/edit each week's result and the final one;
everyone else sees a read-only view.

Deliberately manual, not automated -- admin reviews the leaderboard's
Week tab themselves and records the outcome here, rather than the app
silently auto-assigning forfeits.
"""

from datetime import date

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from db.connection import get_db
from db.models import WeeklyResult, ChallengeSummary, Profile
from routes.auth import get_current_user
from logic.dates import get_target_date_and_lock_status
from logic.leaderboard import get_challenge_start_date, build_range_table

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _require_admin(current_user: Profile | None):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    if not current_user.is_admin:
        return RedirectResponse(url="/", status_code=303)
    return None


def _current_week_number(db: Session) -> int:
    target_date, _ = get_target_date_and_lock_status()
    challenge_start = get_challenge_start_date(db)
    days_elapsed = (target_date - challenge_start).days
    return (days_elapsed // 7) + 1


@router.get("/forfeits", response_class=HTMLResponse)
def forfeits_page(
    request: Request,
    current_user: Profile | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    weekly_results = db.query(WeeklyResult).order_by(WeeklyResult.week_number).all()
    challenge_summary = db.query(ChallengeSummary).first()
    all_users = db.query(Profile).order_by(Profile.display_name).all()

    # For admin convenience, suggest who's currently in last place this
    # week, so they don't have to flip back to the leaderboard to check
    # before recording the forfeit.
    suggested_loser_name = None
    if current_user.is_admin:
        target_date, _ = get_target_date_and_lock_status()
        challenge_start = get_challenge_start_date(db)
        # Monday of the current week, clipped to the challenge's actual
        # start date -- same logic the leaderboard's Week tab uses.
        week_start = target_date.fromordinal(
            target_date.toordinal() - target_date.isoweekday() + 1
        )
        week_start = max(week_start, challenge_start)
        rows = build_range_table(db, week_start, target_date)
        if rows:
            suggested_loser_name = rows[-1]["display_name"]  # last place = highest score

    return templates.TemplateResponse(
        request=request,
        name="forfeits.html",
        context={
            "current_user": current_user,
            "weekly_results": weekly_results,
            "challenge_summary": challenge_summary,
            "all_users": all_users,
            "suggested_week_number": _current_week_number(db),
            "suggested_loser_name": suggested_loser_name,
        },
    )


@router.post("/forfeits/week/save")
def save_weekly_forfeit(
    request: Request,
    week_number: int = Form(...),
    loser_id: str = Form(...),
    forfeit_description: str = Form(...),
    completed: bool = Form(False),
    current_user: Profile | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    redirect = _require_admin(current_user)
    if redirect:
        return redirect

    existing = db.query(WeeklyResult).filter(WeeklyResult.week_number == week_number).first()
    if existing:
        existing.loser_id = loser_id
        existing.forfeit_description = forfeit_description
        existing.completed = completed
    else:
        db.add(WeeklyResult(
            week_number=week_number,
            loser_id=loser_id,
            forfeit_description=forfeit_description,
            completed=completed,
        ))
    db.commit()

    return RedirectResponse(url="/forfeits", status_code=303)


@router.post("/forfeits/final/save")
def save_final_forfeit(
    request: Request,
    loser_id: str = Form(...),
    major_forfeit: str = Form(...),
    completed: bool = Form(False),
    current_user: Profile | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    redirect = _require_admin(current_user)
    if redirect:
        return redirect

    existing = db.query(ChallengeSummary).first()
    if existing:
        existing.loser_id = loser_id
        existing.major_forfeit = major_forfeit
        existing.completed_at = date.today() if completed else None
    else:
        db.add(ChallengeSummary(
            loser_id=loser_id,
            major_forfeit=major_forfeit,
            completed_at=date.today() if completed else None,
        ))
    db.commit()

    return RedirectResponse(url="/forfeits", status_code=303)