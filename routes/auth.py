"""
Authentication routes: login form, login submission, logout.
Uses server-side session cookies (via Starlette's SessionMiddleware) to
track who's logged in -- no public signup, only the 5 pre-created
accounts can log in.
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from db.connection import get_db
from db.models import Profile
from logic.security import verify_password

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
def show_login_form(request: Request, error: str | None = None):
    return templates.TemplateResponse(
        request=request, name="login.html", context={"error": error}
    )

@router.post("/login")
def handle_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.username == username).first()

    # Check both "user exists" and "password matches" -- and importantly,
    # give the SAME error message either way, so a wrong username doesn't
    # accidentally reveal to an attacker which usernames are valid.
    if not profile or not verify_password(password, profile.password_hash):
        return RedirectResponse(
            url="/login?error=Invalid+username+or+password", status_code=303
        )

    if not profile.active:
        return RedirectResponse(
            url="/login?error=This+account+is+no+longer+active", status_code=303
        )

    # Store just the minimal info needed in the session -- the user's id
    # and admin flag. Other routes will look up fresh profile data from
    # the database using this id, rather than trusting stale session data
    # for anything beyond "who is this."
    request.session["user_id"] = str(profile.id)
    request.session["is_admin"] = profile.is_admin

    return RedirectResponse(url="/", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Profile | None:
    """
    FastAPI dependency other routes will use to get the logged-in user
    (or None if not logged in). Always re-fetches from the database
    rather than trusting the session for anything beyond the user id,
    so a permission change (e.g. admin revoked, account deactivated)
    takes effect immediately rather than only after re-login.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return None

    profile = db.query(Profile).filter(Profile.id == user_id).first()
    if not profile or not profile.active:
        return None

    return profile