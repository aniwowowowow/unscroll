"""
Admin-only routes: directly view and edit any user's entries, for any
date, bypassing the normal guided upload flow and its 4pm deadline
entirely. This is the mechanism for admin to manually add/correct data
(e.g. after the deadline locked someone out, or to fix an OCR mistake).

No audit trail by design (per project decision) -- edits overwrite
directly.
"""

from datetime import date as date_type, datetime

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from db.connection import get_db
from db.models import Entry, Profile, WeeklyResult, ChallengeSummary
from routes.auth import get_current_user
from aws.s3_client import get_screenshot_url
from logic.dates import get_target_date_and_lock_status

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _require_admin(current_user: Profile | None):
    """Returns a redirect if not logged in or not an admin, else None."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    if not current_user.is_admin:
        return RedirectResponse(url="/", status_code=303)
    return None


@router.get("/admin/test", response_class=HTMLResponse)
def admin_test():
    return HTMLResponse("<html><body><h1>Test page works</h1></body></html>")


@router.get("/admin/records", response_class=HTMLResponse)
def admin_records_select_user(
    request: Request,
    current_user: Profile | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    redirect = _require_admin(current_user)
    if redirect:
        return redirect

    all_users = db.query(Profile).order_by(Profile.display_name).all()
    return templates.TemplateResponse(
        request=request, name="admin_records_select.html", context={"users": all_users}
    )


@router.get("/admin/records/{user_id}", response_class=HTMLResponse)
def admin_records_view_user(
    request: Request,
    user_id: str,
    current_user: Profile | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    redirect = _require_admin(current_user)
    if redirect:
        return redirect

    target_user = db.query(Profile).filter(Profile.id == user_id).first()
    if not target_user:
        return RedirectResponse(url="/admin/records", status_code=303)

    entries = (
        db.query(Entry)
        .filter(Entry.user_id == user_id)
        .order_by(Entry.entry_date.desc())
        .all()
    )

    # For each entry, check if screenshots are still viewable (within
    # the 7-day S3 lifecycle window) -- generates a signed URL if so,
    # or None if the object has already expired.
    entries_with_urls = []
    for entry in entries:
        total_url = get_screenshot_url(entry.total_screenshot_url) if entry.total_screenshot_url else None
        apps_url = get_screenshot_url(entry.apps_screenshot_url) if entry.apps_screenshot_url else None
        entries_with_urls.append({
            "entry": entry,
            "total_screenshot_url": total_url,
            "apps_screenshot_url": apps_url,
        })

    target_date, _ = get_target_date_and_lock_status()

    return templates.TemplateResponse(
        request=request,
        name="admin_records_view.html",
        context={"target_user": target_user, "entries": entries_with_urls, "today": target_date},
    )


@router.post("/admin/records/{user_id}/edit")
def admin_records_edit_entry(
    request: Request,
    user_id: str,
    entry_date: str = Form(...),
    total_minutes: int = Form(...),
    social_minutes: int = Form(...),
    current_user: Profile | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    redirect = _require_admin(current_user)
    if redirect:
        return redirect

    parsed_date = datetime.strptime(entry_date, "%Y-%m-%d").date()

    # No deadline check here at all -- admin can add/edit any date,
    # any time, which is the whole point of this route.
    existing = (
        db.query(Entry)
        .filter(Entry.user_id == user_id, Entry.entry_date == parsed_date)
        .first()
    )

    if existing:
        existing.total_minutes = total_minutes
        existing.social_minutes = social_minutes
        existing.confirmed = True
    else:
        new_entry = Entry(
            user_id=user_id,
            entry_date=parsed_date,
            total_minutes=total_minutes,
            social_minutes=social_minutes,
            confirmed=True,
        )
        db.add(new_entry)

    db.commit()

    return RedirectResponse(url=f"/admin/records/{user_id}", status_code=303)


@router.post("/admin/records/{user_id}/delete/{entry_id}")
def admin_records_delete_entry(
    request: Request,
    user_id: str,
    entry_id: str,
    current_user: Profile | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    redirect = _require_admin(current_user)
    if redirect:
        return redirect

    entry = db.query(Entry).filter(Entry.id == entry_id, Entry.user_id == user_id).first()
    if entry:
        db.delete(entry)
        db.commit()

    return RedirectResponse(url=f"/admin/records/{user_id}", status_code=303)


@router.post("/admin/records/{user_id}/toggle-active")
def admin_toggle_active(
    request: Request,
    user_id: str,
    current_user: Profile | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    redirect = _require_admin(current_user)
    if redirect:
        return redirect

    target_user = db.query(Profile).filter(Profile.id == user_id).first()
    if target_user and target_user.id != current_user.id:
        # Prevent admin from accidentally deactivating themselves --
        # that would lock them out of the admin tools entirely.
        target_user.active = not target_user.active
        db.commit()

    return RedirectResponse(url=f"/admin/records/{user_id}", status_code=303)


@router.post("/admin/records/{user_id}/delete-user")
def admin_delete_user(
    request: Request,
    user_id: str,
    current_user: Profile | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    redirect = _require_admin(current_user)
    if redirect:
        return redirect

    target_user = db.query(Profile).filter(Profile.id == user_id).first()
    if not target_user or target_user.id == current_user.id:
        # Refuse to delete yourself -- would lock the only admin out.
        return RedirectResponse(url="/admin/records", status_code=303)

    # Delete all of their entries first (the foreign key would otherwise
    # block deleting the profile row while entries still reference it).
    db.query(Entry).filter(Entry.user_id == user_id).delete()

    # Clear any historical forfeit/summary references to this user too,
    # rather than leaving a dangling reference to a deleted profile.
    db.query(WeeklyResult).filter(WeeklyResult.loser_id == user_id).update(
        {WeeklyResult.loser_id: None}
    )
    db.query(ChallengeSummary).filter(ChallengeSummary.loser_id == user_id).update(
        {ChallengeSummary.loser_id: None}
    )

    db.delete(target_user)
    db.commit()

    return RedirectResponse(url="/admin/records", status_code=303)
@router.post("/admin/reset-challenge")
def admin_reset_challenge(
    request: Request,
    current_user: Profile | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    redirect = _require_admin(current_user)
    if redirect:
        return redirect

    db.query(Entry).delete()
    db.query(WeeklyResult).delete()
    db.query(ChallengeSummary).delete()
    db.commit()

    return RedirectResponse(url="/admin/records", status_code=303)