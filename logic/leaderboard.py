"""
Builds the data for the three leaderboard tabs (Today / Week / Total)
by reusing the same daily scoring logic (logic/scoring.py) for each
individual day, then summing across a date range for the Week and
Total tabs.
"""

from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import Entry, Profile
from logic.scoring import DailyEntry, calculate_daily_scores


def _format_minutes(minutes: int) -> str:
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"


def get_challenge_start_date(db: Session) -> date:
    earliest = db.query(func.min(Entry.entry_date)).scalar()
    return earliest if earliest else date.today()


def _get_active_profiles(db: Session) -> list[Profile]:
    return db.query(Profile).filter(Profile.active == True).all()  # noqa: E712


def build_daily_table(db: Session, target_date: date) -> list[dict]:
    profiles = _get_active_profiles(db)
    profile_lookup = {str(p.id): p for p in profiles}

    daily_entries = []
    for profile in profiles:
        entry = (
            db.query(Entry)
            .filter(Entry.user_id == profile.id, Entry.entry_date == target_date)
            .first()
        )
        daily_entries.append(DailyEntry(
            user_id=str(profile.id),
            total_minutes=entry.total_minutes if entry else None,
            social_minutes=entry.social_minutes if entry else None,
        ))

    results = calculate_daily_scores(daily_entries)
    results.sort(key=lambda r: r.combined_score)

    rows = []
    for r in results:
        profile = profile_lookup[r.user_id]
        rows.append({
            "display_name": profile.display_name,
            "missed": not r.uploaded,
            "total_display": _format_minutes(r.total_minutes) if r.uploaded else "--",
            "social_display": _format_minutes(r.social_minutes) if r.uploaded else "--",
            "total_points": r.total_points,
            "social_points": r.social_points,
            "combined_score": r.combined_score,
        })
    return rows


def build_range_table(db: Session, start_date: date, end_date: date) -> list[dict]:
    profiles = _get_active_profiles(db)
    profile_lookup = {str(p.id): p for p in profiles}

    totals = {
        str(p.id): {
            "total_minutes_sum": 0,
            "social_minutes_sum": 0,
            "total_points_sum": 0,
            "social_points_sum": 0,
            "combined_score_sum": 0,
            "missed_days": 0,
        }
        for p in profiles
    }

    current_day = start_date
    while current_day <= end_date:
        daily_entries = []
        for profile in profiles:
            entry = (
                db.query(Entry)
                .filter(Entry.user_id == profile.id, Entry.entry_date == current_day)
                .first()
            )
            daily_entries.append(DailyEntry(
                user_id=str(profile.id),
                total_minutes=entry.total_minutes if entry else None,
                social_minutes=entry.social_minutes if entry else None,
            ))

        day_results = calculate_daily_scores(daily_entries)
        for r in day_results:
            totals[r.user_id]["total_points_sum"] += r.total_points
            totals[r.user_id]["social_points_sum"] += r.social_points
            totals[r.user_id]["combined_score_sum"] += r.combined_score
            if r.uploaded:
                totals[r.user_id]["total_minutes_sum"] += r.total_minutes
                totals[r.user_id]["social_minutes_sum"] += r.social_minutes
            else:
                totals[r.user_id]["missed_days"] += 1

        current_day += timedelta(days=1)

    rows = []
    for user_id, data in totals.items():
        profile = profile_lookup[user_id]
        rows.append({
            "display_name": profile.display_name,
            "missed_days": data["missed_days"],
            "total_display": _format_minutes(data["total_minutes_sum"]),
            "social_display": _format_minutes(data["social_minutes_sum"]),
            "total_points": data["total_points_sum"],
            "social_points": data["social_points_sum"],
            "combined_score": data["combined_score_sum"],
        })

    rows.sort(key=lambda r: r["combined_score"])
    return rows