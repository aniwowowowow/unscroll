"""
The 4-step guided upload flow:
  1. Upload total screentime screenshot
  2. Upload top-apps screenshot
  3. Confirm/correct the OCR-extracted numbers
  4. Submit -> see today's rank

Uses the session to hold temporary state between steps (S3 keys, OCR
results) -- nothing is written to the database until the final submit.
"""

from datetime import date

from fastapi import APIRouter, Request, Depends, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from db.connection import get_db
from db.models import Entry, Profile
from routes.auth import get_current_user
from aws.s3_client import upload_screenshot
from logic.ocr_utils import extract_total_minutes, extract_social_minutes
from logic.scoring import DailyEntry, calculate_daily_scores
from logic.dates import get_target_date_and_lock_status as _get_target_date_and_lock_status

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _require_login(current_user: Profile | None):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    return None


@router.get("/upload/step1", response_class=HTMLResponse)
def upload_step1_form(request: Request, current_user: Profile | None = Depends(get_current_user)):
    redirect = _require_login(current_user)
    if redirect:
        return redirect

    target_date, locked = _get_target_date_and_lock_status()
    if locked:
        return templates.TemplateResponse(
            request=request, name="upload_locked.html", context={"target_date": target_date}
        )

    return templates.TemplateResponse(request=request, name="upload_step1.html", context={})


@router.post("/upload/step1")
async def upload_step1_submit(
    request: Request,
    screenshot: UploadFile = File(...),
    current_user: Profile | None = Depends(get_current_user),
):
    redirect = _require_login(current_user)
    if redirect:
        return redirect

    _, locked = _get_target_date_and_lock_status()
    if locked:
        return RedirectResponse(url="/upload/step1", status_code=303)

    file_bytes = await screenshot.read()

    s3_key = upload_screenshot(file_bytes, str(current_user.id), "total")
    total_minutes, total_confident = extract_total_minutes(file_bytes)

    request.session["upload_total_key"] = s3_key
    request.session["upload_total_minutes"] = total_minutes
    request.session["upload_total_confident"] = total_confident

    return RedirectResponse(url="/upload/step2", status_code=303)


@router.get("/upload/step2", response_class=HTMLResponse)
def upload_step2_form(request: Request, current_user: Profile | None = Depends(get_current_user)):
    redirect = _require_login(current_user)
    if redirect:
        return redirect
    if "upload_total_key" not in request.session:
        return RedirectResponse(url="/upload/step1", status_code=303)
    return templates.TemplateResponse(request=request, name="upload_step2.html", context={})


@router.post("/upload/step2")
async def upload_step2_submit(
    request: Request,
    screenshot: UploadFile = File(...),
    current_user: Profile | None = Depends(get_current_user),
):
    redirect = _require_login(current_user)
    if redirect:
        return redirect

    file_bytes = await screenshot.read()

    s3_key = upload_screenshot(file_bytes, str(current_user.id), "apps")
    social_minutes, social_confident = extract_social_minutes(file_bytes)

    request.session["upload_apps_key"] = s3_key
    request.session["upload_social_minutes"] = social_minutes
    request.session["upload_social_confident"] = social_confident

    return RedirectResponse(url="/upload/confirm", status_code=303)


@router.get("/upload/confirm", response_class=HTMLResponse)
def upload_confirm_form(request: Request, current_user: Profile | None = Depends(get_current_user)):
    redirect = _require_login(current_user)
    if redirect:
        return redirect
    if "upload_apps_key" not in request.session:
        return RedirectResponse(url="/upload/step2", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="upload_confirm.html",
        context={
            "total_minutes": request.session.get("upload_total_minutes"),
            "total_confident": request.session.get("upload_total_confident"),
            "social_minutes": request.session.get("upload_social_minutes"),
            "social_confident": request.session.get("upload_social_confident"),
        },
    )


@router.post("/upload/confirm")
def upload_confirm_submit(
    request: Request,
    total_minutes: int = Form(...),
    social_minutes: int = Form(...),
    current_user: Profile | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    redirect = _require_login(current_user)
    if redirect:
        return redirect

    target_date, locked = _get_target_date_and_lock_status()
    if locked:
        return RedirectResponse(url="/upload/step1", status_code=303)

    existing = (
        db.query(Entry)
        .filter(Entry.user_id == current_user.id, Entry.entry_date == target_date)
        .first()
    )

    if existing:
        existing.total_minutes = total_minutes
        existing.social_minutes = social_minutes
        existing.total_screenshot_url = request.session.get("upload_total_key")
        existing.apps_screenshot_url = request.session.get("upload_apps_key")
        existing.confirmed = True
    else:
        new_entry = Entry(
            user_id=current_user.id,
            entry_date=target_date,
            total_minutes=total_minutes,
            social_minutes=social_minutes,
            total_screenshot_url=request.session.get("upload_total_key"),
            apps_screenshot_url=request.session.get("upload_apps_key"),
            confirmed=True,
        )
        db.add(new_entry)

    db.commit()

    for key in ["upload_total_key", "upload_total_minutes", "upload_total_confident",
                "upload_apps_key", "upload_social_minutes", "upload_social_confident"]:
        request.session.pop(key, None)

    return RedirectResponse(url="/upload/done", status_code=303)


@router.get("/upload/done", response_class=HTMLResponse)
def upload_done(request: Request, current_user: Profile | None = Depends(get_current_user), db: Session = Depends(get_db)):
    redirect = _require_login(current_user)
    if redirect:
        return redirect

    target_date, _ = _get_target_date_and_lock_status()

    all_users = db.query(Profile).filter(Profile.active == True).all()  # noqa: E712
    daily_entries = []
    for user in all_users:
        entry = (
            db.query(Entry)
            .filter(Entry.user_id == user.id, Entry.entry_date == target_date)
            .first()
        )
        daily_entries.append(DailyEntry(
            user_id=str(user.id),
            total_minutes=entry.total_minutes if entry else None,
            social_minutes=entry.social_minutes if entry else None,
        ))

    results = calculate_daily_scores(daily_entries)
    my_result = next(r for r in results if r.user_id == str(current_user.id))

    return templates.TemplateResponse(
        request=request,
        name="upload_done.html",
        context={
            "total_rank": my_result.total_rank,
            "social_rank": my_result.social_rank,
            "combined_score": my_result.combined_score,
        },
    )