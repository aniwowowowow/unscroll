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
- Automated OCR extraction (Gemini API) of both total screentime and
  social-media-specific screentime (summed from a known app list),
  with confidence-based fallback to manual entry
- Manual confirm/correct step after OCR, since automated extraction
  isn't always 100% accurate
- Dual-path ranking system per day:
  - Total screentime rank -> points (linear)
  - Social media screentime rank -> points (steeper, punishing curve)
  - Competition-style tie handling (tied ranks share a position, next
    rank skips ahead)
  - Missing an upload = automatic worst-case score on both paths
  - Group size is dynamic -- scoring adapts if someone is deactivated
    or removed mid-challenge
- Weekly and 100-day cumulative leaderboards, plus a 100-day progress bar
- Forfeit tracking: weekly loser + a major forfeit for the 100-day loser
- Full admin panel: edit/delete any entry, deactivate/delete users,
  reset all challenge data
- Deployed on AWS EC2 with HTTPS

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend framework | FastAPI (Python) | Type-safe request validation, auto-generated docs, modern async support |
| Database | PostgreSQL on AWS RDS | Managed Postgres, free-tier eligible at this project's scale |
| File storage | AWS S3 | Standard, cheap object storage for screenshots; lifecycle rule auto-deletes old images |
| OCR | Gemini API (`google-genai`) | Multimodal understanding, not just text transcription -- can distinguish the real total screentime from unrelated numbers (chart labels, etc.); free at this project's scale |
| Hosting | AWS EC2 (`t3.micro`) | Free-tier eligible, simple single-instance deployment for a small user base |
| Templating | Jinja2 | Server-rendered HTML, no separate frontend framework needed at this scale |

## Architecture (high level)

```
Browser (upload form)
      |
      v
FastAPI app (EC2)  -----> S3 (stores screenshots, 3-day lifecycle)
      |
      v
Gemini API --> context-aware extraction of total + social minutes
      |
      v
Scoring logic (Python) --> ranks + points per day, dynamic group size
      |
      v
RDS Postgres  <-- stores entries, weekly results, challenge summary
      |
      v
Leaderboard / admin / forfeits pages (Jinja2 + shared CSS)
      |
      v
Nginx (reverse proxy, HTTPS via Let's Encrypt) --> the internet
```

## Key design decisions

- **Rank-based scoring instead of raw-minute weighting.** Ranking is more
  robust to small OCR misreads (a few minutes off doesn't change your
  effective score) compared to weighting raw minutes directly.
- **Two ranking paths (total vs. social), with social weighted more
  punitively.** This rewards cutting "junk" scrolling specifically,
  not just any screen time (e.g., work-related phone use isn't
  penalized as harshly as social media use).
- **Fixed group of 5 by default, but scoring is dynamic** -- point
  scales are computed from whoever's currently active, not hardcoded,
  so the app still works correctly if someone is deactivated or
  removed mid-challenge.
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
    if within 3 days of upload** (see S3 lifecycle rule below). Older
    entries show "Screenshots no longer available (past 3-day
    retention)" instead of a broken image -- the recorded minutes stay
    editable regardless of screenshot age.
- **Manage Users** -- add a new profile (e.g. someone joins late) or
  remove/deactivate one (e.g. someone drops out mid-challenge)
- **No audit trail on admin edits** -- a deliberate simplicity choice for
  a small, trusted friend group; edits overwrite directly with no log of
  who/what/when changed

### Data retention

- Screenshots are stored in S3 and **auto-deleted 3 days after upload**
  via an S3 Lifecycle Rule (rolling per-object expiration, not aligned to
  calendar weeks) -- no custom code needed, S3 handles this natively.
- The database row (including the now-broken screenshot URL) is never
  deleted -- only the S3 object expires. The app must handle a stored
  URL pointing to an already-expired object gracefully.

## Deployment to EC2 (remaining steps)

Local development is fully done and tested. This is the roadmap for
putting it on a real, always-on server. Pick up here.

### 1. Launch the EC2 instance
- Ubuntu 24.04 LTS, `t3.micro` (confirm "Free tier eligible")
- Create a new key pair (`.pem` file) -- save it somewhere safe, needed
  for every future SSH connection
- Security group: allow SSH from "My IP" only, allow HTTP (port 80)
  and HTTPS (port 443) from anywhere

### 2. Connect via SSH
```bash
chmod 400 unscroll-key.pem          # required permission fix, once
ssh -i unscroll-key.pem ubuntu@<EC2-public-IP>
```

### 3. Install system dependencies on the instance
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git nginx
```
(No Tesseract needed anymore -- OCR is Gemini API, not local.)

### 4. Clone the repo and set up the environment
```bash
git clone <your-github-repo-url>
cd unscroll
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Recreate `.env` on the server
`.env` is gitignored (correctly), so it won't come from GitHub -- create
it fresh on the instance with the same values as local (`DATABASE_URL`,
AWS keys, `GEMINI_API_KEY`, `SESSION_SECRET_KEY`, `S3_BUCKET_NAME`,
`AWS_REGION`). Use `nano .env` to create/paste it directly on the server.

**Better long-term practice**: once this works, switch AWS credentials to
an IAM Role attached directly to the EC2 instance instead of static
keys in `.env` -- more secure, no long-lived secret sitting on disk.
Revisit this after the basic deployment works.

### 6. Update RDS security
- RDS's security group should allow inbound Postgres traffic from
  EC2's security group (not "My IP" anymore, since traffic now comes
  from AWS's internal network)
- Consider switching RDS "Public access" back to **No** once EC2 is the
  only thing that needs to reach it -- tightens the attack surface

### 7. Run the app as a persistent service
Don't just run `uvicorn` in the SSH session -- it'll die when you
disconnect. Use `systemd` so it runs continuously and restarts on
reboot:
```bash
sudo nano /etc/systemd/system/unscroll.service
```
```ini
[Unit]
Description=Unscroll FastAPI app
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/unscroll
ExecStart=/home/ubuntu/unscroll/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable unscroll
sudo systemctl start unscroll
sudo systemctl status unscroll   # confirm it's running
```

### 8. Put Nginx in front of it
Nginx acts as a reverse proxy -- forwards normal web traffic (port 80)
to your app (port 8000), and will also handle HTTPS later:
```bash
sudo nano /etc/nginx/sites-available/unscroll
```
```nginx
server {
    listen 80;
    server_name <EC2-public-IP-or-domain>;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
```bash
sudo ln -s /etc/nginx/sites-available/unscroll /etc/nginx/sites-enabled/
sudo nginx -t      # test the config
sudo systemctl restart nginx
```

### 9. Test it
Visit `http://<EC2-public-IP>` in a browser -- should show the real
login page, not a placeholder.

### 10. Security hardening before real use
- HTTPS via Let's Encrypt (`certbot`) -- free, standard, pairs with
  Nginx -- needed if this ever has a real domain name pointed at it
- Confirm RDS public access is off (step 6)
- Double-check `.env` on the server has correct real values and is not
  world-readable (`chmod 600 .env`)

### 11. End-of-challenge cleanup
Once the 100 days are done: **terminate the EC2 instance and the RDS
instance** (not just "stop" -- a stopped instance with an attached EBS
volume, or a stopped RDS instance, still incurs storage charges).
Empty and delete the S3 bucket too if it's no longer needed.

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
- [x] Database models defined and tables created (`profiles`, `entries`, `weekly_results`, `challenge_summary`) -- verified visually via pgAdmin
- [x] Create initial user accounts (5 profiles, hashed passwords, one admin)
- [x] S3 upload integration (`aws/s3_client.py` -- upload + signed URL retrieval, confirmed with `test_s3.py`)
- [x] OCR pipeline (`logic/ocr_utils.py` -- using Gemini API for
      context-aware extraction, plus `logic/social_apps.py`)
- [x] Login/auth route (`routes/auth.py`, `logic/security.py`,
      `templates/login.html` -- session-based, no public signup)
- [x] Upload/scoring/leaderboard routes (`routes/entries.py`,
      `routes/leaderboard.py`, `logic/leaderboard.py`, `logic/dates.py`)
- [x] Admin tools (`routes/admin.py` -- view/edit/delete any entry,
      deactivate or fully delete a user, screenshot viewing within the
      3-day window)
- [x] Forfeits page (`routes/forfeits.py`, `templates/forfeits.html` --
      weekly loser history + final forfeit, admin records both with a
      suggested loser pre-filled from the current week's standings)
- [x] Design pass across all pages (shared `static/style.css`, Manrope
      font, forest green + warm gold palette, logo on login/home,
      mobile-friendly)
- [x] 100-day progress bar on the leaderboard
- [x] Deployed to EC2 (Amazon Linux 2023, Python 3.12, systemd service,
      Nginx reverse proxy on port 80)
- [x] HTTPS via Let's Encrypt/Certbot, using a free sslip.io domain
      (embeds the EC2 IP directly in the hostname, e.g.
      `1-2-3-4.sslip.io` -- no signup needed, since Let's Encrypt can't
      issue certificates for a bare IP address, only a real domain name)

The app is feature-complete and deployed. Remaining items are
operational, not technical: share the live link with the group, and
communicate the temporary passwords (no self-service password change
exists yet).

### Notes on setup gotchas encountered

- Used `pg8000` instead of `psycopg2-binary` -- Windows blocked psycopg2's
  compiled DLL (Application Control / Smart App Control). `pg8000` is a
  pure-Python driver with no compiled components, avoiding the issue
  entirely, and works the same with SQLAlchemy.
- RDS instance must have "Public access" set to Yes to be reachable from
  a local machine at all -- a correctly configured security group alone
  isn't enough if public access is off.
- `passlib` is incompatible with `bcrypt` 4.1+ (a missing `__about__`
  attribute causes a confusing "password cannot be longer than 72 bytes"
  error even on short passwords). Fixed by pinning `bcrypt==4.0.1`.
- If a Python script can't find a variable that's clearly in `.env`,
  confirm the file actually saved (VS Code's unsaved-changes dot) and
  run `Get-Content .env` in the terminal to see the real file contents
  directly, rather than trusting what the editor shows.
- S3 bucket names must match exactly, character for character -- a
  typo produces a `NoSuchBucket` error that can look like an auth
  problem at first glance but isn't. Note: since bucket names must be
  globally unique across all of AWS, the real bucket name ended up
  being `unscroll-sc` plus extra generated characters, not the plain
  name -- always check the S3 console for the exact real name rather
  than assuming.
- OCR engine went through three iterations: Tesseract (local, free,
  but noticeably less accurate on real screenshots and blind to
  context -- e.g. confused a chart axis label for the real total) ->
  AWS Textract (accurate, AWS-native, ~$1.50 total for the whole
  challenge, but free tier is time-limited to 3 months not ongoing) ->
  **Gemini API** (final choice -- genuinely free at this project's
  scale, and being a full multimodal model rather than plain OCR, it
  can be prompted to understand *which* number is the real total vs.
  an unrelated figure on screen, rather than just transcribing
  everything it sees).
- Google deprecated the `google-generativeai` package in favor of
  `google-genai` -- different API shape (`genai.Client()` instead of
  `genai.configure()` + `GenerativeModel`). Model names also change
  over time (`gemini-2.0-flash` was retired in favor of
  `gemini-3.6-flash` during this project) -- if a Gemini call 404s,
  check the current model name rather than assuming the code is wrong.
- The recurring "code change doesn't seem to take effect" bug across
  this project was almost always stale `__pycache__` files -- clear
  them (`Get-ChildItem -Recurse -Directory -Filter __pycache__ |
  Remove-Item -Recurse -Force`) whenever behavior doesn't match a
  recent edit.
- The Gemini prompt for total-time extraction needed refinement to be
  reliably accurate: telling it to find the LARGEST, most prominent
  number closest to a "Total screen time" label (and explicitly
  contrasting that against smaller chart axis/gridline numbers)
  resolved cases where it initially picked up an unrelated chart label
  instead of the real total.
- EC2's default Python (3.9 on Amazon Linux 2023) is too old for this
  codebase's `X | None` type hint syntax (needs 3.10+) -- installed
  Python 3.12 alongside the system default and rebuilt the venv with
  it specifically (`python3.12 -m venv venv`), rather than editing
  every type hint in the codebase.
- Let's Encrypt cannot issue a certificate for a bare IP address, only
  for a real domain name -- used sslip.io (free, no signup, embeds the
  IP directly in the hostname) instead of a traditional domain
  purchase or DuckDNS account.
- EC2's default public IP changes if the instance is ever stopped and
  restarted (unless an Elastic IP is attached) -- since the sslip.io
  domain and DNS both depend on that IP, a restart would require
  redoing the Nginx/Certbot setup with the new address. Not an issue
  for an instance left running continuously for the challenge's
  duration.
- Amazon Linux 2023 uses `dnf` (not `apt`), `/etc/nginx/conf.d/` for
  site configs (not `sites-available`/`sites-enabled`), and ships
  Certbot directly in its own repos (`sudo dnf install certbot
  python3-certbot-nginx`) -- no third-party repo or manual venv
  workaround needed.
- Newer FastAPI/Starlette versions expect `TemplateResponse(request=
  request, name="x.html", context={...})` rather than the older
  `TemplateResponse("x.html", {"request": request, ...})` style --
  using the old style on a newer install caused a confusing internal
  Jinja2 caching error (`cannot use 'tuple' as a dict key`) rather than
  a clear "wrong arguments" message.
- Double-check which folder a template file actually landed in --
  `TemplateNotFound` with a file that visibly exists usually means it's
  sitting in the wrong folder (e.g. `routes/` instead of `templates/`),
  not that the file is missing.
- Windows' `zoneinfo` module has no built-in timezone database (unlike
  Linux/Mac) -- install the `tzdata` package to fix
  `ZoneInfoNotFoundError`, no code changes needed.
- Scoring was originally hardcoded to exactly 5 people (`GROUP_SIZE`
  constant with fixed point-lookup tables). Supporting a shrinking
  group (deactivating/deleting a user mid-challenge) required
  generalizing the social-media point curve into a formula
  (`_social_points_for_rank`) that reproduces the original tuned curve
  (1, 2, 3, 5, 7) at 5 people but scales to any group size. Group size
  is now just `len(entries)` for a given calculation, not a constant --
  note this means past days get recalculated with the CURRENT active
  count if someone is later removed, consistent with the project's
  "no audit trail, always recompute fresh" design.
- Deleting a user requires deleting their `Entry` rows first (and
  nulling any `WeeklyResult`/`ChallengeSummary` references) before the
  `Profile` row itself can be deleted, due to the foreign key
  relationship -- otherwise Postgres rejects the delete.
- RDS storage autoscaling can silently grow allocated storage past the
  20GB free-tier threshold, adding an ongoing monthly cost. Storage can
  only be increased, never shrunk back down without recreating the
  instance -- turn autoscaling off explicitly rather than relying on
  the free-tier default.
- A recurring theme throughout this build: many confusing errors
  (`ModuleNotFoundError` on a file that exists, `ImportError` on a
  function that's clearly defined, stale behavior after an edit) were
  actually stale `__pycache__` bytecode -- clearing it
  (`Get-ChildItem -Recurse -Directory -Filter __pycache__ |
  Remove-Item -Recurse -Force`) before assuming a deeper bug saved
  significant debugging time.

## License

Personal/portfolio project -- not currently licensed for reuse.