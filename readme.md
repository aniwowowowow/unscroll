# Unscroll

A 100-day screentime accountability challenge app built for a group of 5 friends.
Each day, everyone uploads screenshots of their phone's screentime summary; the
app extracts the numbers automatically via OCR, ranks everyone, and tracks
weekly and overall "losers" who owe a forfeit.

## Why this project

Built to (a) actually keep a friend group honest about screen time, and (b) act
as a full-stack, cloud-deployed portfolio project demonstrating backend API
design, database modeling, OCR/image processing, and AWS infrastructure.

## Features

- Two-screenshot daily upload: one for total screentime, one for the
  top-apps breakdown
- Automated OCR extraction (Tesseract) of both total screentime and
  social-media-specific screentime (summed from a known app list)
- Manual confirm/correct step after OCR, since automated extraction
  isn't always 100% accurate
- Dual-path ranking system per day:
  - Total screentime rank -> points (linear: 1-5)
  - Social media screentime rank -> points (steeper: 1,2,3,5,7)
  - Competition-style tie handling (tied ranks share a position, next
    rank skips ahead)
  - Missing an upload = automatic worst-case score on both paths
- Weekly and 100-day cumulative leaderboards
- Forfeit tracking: weekly loser + a major forfeit for the 100-day loser

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend framework | FastAPI (Python) | Type-safe request validation, auto-generated docs, modern async support |
| Database | PostgreSQL on AWS RDS | Managed Postgres, free-tier eligible at this project's scale |
| File storage | AWS S3 | Standard, cheap object storage for screenshots; lifecycle rule auto-deletes old images |
| OCR | Tesseract via `pytesseract` | Free, self-hosted, no per-request cost, accurate enough for clean phone-UI text |
| Hosting | AWS EC2 (`t3.micro`) | Free-tier eligible, simple single-instance deployment for a small user base |
| Templating | Jinja2 | Server-rendered HTML, no separate frontend framework needed at this scale |

## Architecture (high level)

```
Browser (upload form)
      |
      v
FastAPI app (EC2)  -----> S3 (stores screenshots)
      |
      v
Tesseract OCR (on EC2) --> parses total + social minutes
      |
      v
Scoring logic (Python) --> ranks + points per day
      |
      v
RDS Postgres  <-- stores entries, weekly results, challenge summary
      |
      v
Leaderboard / dashboard pages (Jinja2 templates)
```

## Key design decisions

- **Rank-based scoring instead of raw-minute weighting.** Ranking is more
  robust to small OCR misreads (a few minutes off doesn't change your
  effective score) compared to weighting raw minutes directly.
- **Two ranking paths (total vs. social), with social weighted more
  punitively.** This rewards cutting "junk" scrolling specifically,
  not just any screen time (e.g., work-related phone use isn't
  penalized as harshly as social media use).
- **Fixed group size (5), so point scales are hardcoded** rather than
  dynamically generated -- simpler, and matches the actual use case.
- **Missing an upload scores as the worst possible rank on both paths**,
  rather than being excluded from ranking -- this avoids accidentally
  rewarding non-participation.
- **Two screenshots per day (total + top apps)** instead of one, since
  both numbers are needed but aren't always shown together in one view
  across iOS/Android layouts. A fixed, code-maintained list of "social"
  app names is used to sum social media time from the app breakdown.

## UI / UX specification

### Pages

**Login**
- 5 pre-created accounts only -- no public signup, no self-registration
- Session-based login; one of the 5 accounts is flagged `is_admin = True`

**Leaderboard (main/landing page)**
- Three tabs: **Today**, **This Week (so far)**, **Total Competition (so far)**
- Columns (same structure across all tabs): Rank, Name, Total Screentime,
  Social Screentime, Total Points, Social Points, Combined Score
- Sorted ascending by Combined Score (lowest = best, matches "minimize
  your score" goal)
- **Today tab:** missed upload shows a dash for time columns, single flag
  next to the name, and max-score points (5 total + 7 social = 12) applied
- **Week / Total tabs:** raw minutes are summed across the period and
  displayed as `Xh Ym`; missed days are shown as a compact count next to
  the name, e.g. `Bob (2x🚩)`, rather than one flag per missed day; points
  are always summed regardless of missed days

**Upload flow (guided, 4 steps)**
1. Upload total screentime screenshot (preview shown, Next disabled until
   a file is chosen)
2. Upload top-apps screenshot (same pattern, Back/Next)
3. Confirm OCR results -- editable fields for total and social minutes.
   If OCR confidence is high, the field is pre-filled (still editable).
   If confidence is low, the field is left **blank** with a prompt to
   enter the value manually, rather than showing a possibly-wrong guess.
4. Submit -> confirmation screen showing "Submitted!" plus the user's
   **current rank for today** immediately

**Forfeits**
- Weekly loser history (who, what forfeit, completed y/n)
- Final 100-day major forfeit tracker

**Admin (visible only to the one `is_admin = True` account)**
- Extra controls appear inline on existing pages rather than a separate
  app -- enforced both by hiding UI elements in templates AND by checking
  `is_admin` again server-side on every admin route, since hiding a
  button is not real access control on its own
- **Edit icon on leaderboard rows** -- quick edit of *today's* entry for
  any user (shortcut into the same edit capability as the Records page)
- **Records page** -- select any user, see their full entry history
  (date, total/social minutes, confirmed status, missed-day flag), with
  inline edit per row
  - Each entry can show its original screenshots (total + apps) **only
    if within 7 days of upload** (see S3 lifecycle rule below). Older
    entries show "Screenshots no longer available (past 7-day
    retention)" instead of a broken image -- the recorded minutes stay
    editable regardless of screenshot age.
- **Manage Users** -- add a new profile (e.g. someone joins late) or
  remove/deactivate one (e.g. someone drops out mid-challenge)
- **No audit trail on admin edits** -- a deliberate simplicity choice for
  a small, trusted friend group; edits overwrite directly with no log of
  who/what/when changed

### Data retention

- Screenshots are stored in S3 and **auto-deleted 7 days after upload**
  via an S3 Lifecycle Rule (rolling per-object expiration, not aligned to
  calendar weeks) -- no custom code needed, S3 handles this natively.
- The database row (including the now-broken screenshot URL) is never
  deleted -- only the S3 object expires. The app must handle a stored
  URL pointing to an already-expired object gracefully.

## Setup / running locally

```bash
git clone <repo-url>
cd unscroll
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
```

Create a `.env` file (never committed) with:

```
DATABASE_URL=postgresql://<user>:<password>@<rds-endpoint>:5432/<dbname>
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=...
S3_BUCKET_NAME=...
```

Run the app:

```bash
uvicorn main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for the interactive API documentation.

## Project status

- [x] Local dev environment set up (FastAPI + Uvicorn running)
- [x] Scoring logic implemented (`logic/scoring.py`)
- [x] RDS database provisioned and connected (via `pg8000`, confirmed with `test_connection.py`)
- [ ] Database models defined
- [ ] S3 upload integration
- [ ] OCR pipeline (`logic/ocr_utils.py`)
- [ ] Upload/scoring/leaderboard routes
- [ ] HTML templates
- [ ] Deployed to EC2

### Notes on setup gotchas encountered

- Used `pg8000` instead of `psycopg2-binary` -- Windows blocked psycopg2's
  compiled DLL (Application Control / Smart App Control). `pg8000` is a
  pure-Python driver with no compiled components, avoiding the issue
  entirely, and works the same with SQLAlchemy.
- RDS instance must have "Public access" set to Yes to be reachable from
  a local machine at all -- a correctly configured security group alone
  isn't enough if public access is off.

## License

Personal/portfolio project -- not currently licensed for reuse.