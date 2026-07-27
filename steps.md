# Build Steps — Cold Mail Automation (Multi-User)

Follow in order. Do not skip ahead — each step depends on the one before it. Do not build any UI/frontend at any point in this list; backend + API only, tested via curl/HTTP client. UI comes later from a separate `design.md`.

## Step 1 — Project scaffold (DONE)
- Initialize FastAPI project structure (app/, models/, routers/, services/, workers/, migrations/)
- Set up Postgres connection (Neon/Supabase) via env var `DATABASE_URL`
- Set up a migration tool (Alembic)
- Add `.env.example` listing every required app-level env var (Section 8 of project_idea.md)
- Health check endpoint (`GET /health`) working end-to-end before moving on

## Step 2 — Multi-user auth (DONE)
- `users` table (id, email, password_hash, created_at)
- `POST /auth/signup`, `POST /auth/login` (JWT returned)
- Middleware resolving `user_id` from the token on every protected route
- Confirm explicitly: create two test users, verify a request with user A's token cannot read/write user B's rows on any table — this is the core security check for the whole build, don't move on until it passes

## Step 3 — Settings (per-user secrets) (DONE)
- `settings` table (user_id, smtp_host/user/app_password [encrypted], imap_host/user/app_password [encrypted], linkedin_cookie [encrypted], send_mode, schedule_window)
- CRUD API for a user to set their own SMTP/IMAP/LinkedIn creds and preferences
- Confirm: secrets are encrypted at rest, not stored/logged in plaintext anywhere

## Step 4 — Object storage + resume upload (DONE)
- Connect object storage bucket (Supabase Storage or S3-compatible) via `STORAGE_BUCKET_URL`/keys
- `resumes` table (id, user_id, file_url, uploaded_at, parsed_status)
- `POST /resume/upload` — accepts PDF/doc, stores in bucket, creates `resumes` row with `parsed_status = pending`
- Confirm: upload a real resume, verify the file is retrievable from the bucket

## Step 5 — Context Layer tables (empty, per user) (DONE)
- Create tables: `context_profile`, `context_experience`, `context_projects`, `context_achievements` — all with `user_id` FK
- Build full CRUD API for each, scoped to the authenticated user
- Confirm: two test users can each create/edit their own context entries without seeing each other's

## Step 6 — LLM Resume Parser (DONE)
- Background job: pick up `resumes` rows with `parsed_status = pending`, extract text from the file, send to LLM with a strict "extract into this exact JSON schema" prompt (schema = `context_layer_seed.json`'s shape)
- Write the parsed output into that user's `context_profile`/`context_experience`/`context_projects`/`context_achievements` rows
- Update `resumes.parsed_status = done`
- Confirm: upload your own resume (or a sample), verify the parsed context in the DB against `context_layer_seed.json` for shape correctness

## Step 7 — Templates table (per user, editable) (DONE)
- Create `templates` table with `user_id` FK
- On signup (Step 2), auto-seed each new user with the 5 default templates from `templates.md`
- Full CRUD API scoped per user, so users can edit/replace/add categories freely
- Confirm: editing user A's template does not affect user B's

## Step 8 — Contacts store (DONE)
- Create `contacts` and `scrape_queue` tables, both with `user_id` FK
- Manual test-insert endpoint to confirm status transitions (`new -> personalized -> queued -> sent`) work per user before any scraper exists

## Step 9 — Scrapers (build in this order, safest first) (DONE)
1. Career-page scraper (static HTML) — writes to `scrape_queue`
2. GitHub/AngelList public scraper
3. Job portal scraper (Naukri/Indeed/LinkedIn Jobs listings)
4. LinkedIn scraper last, using each user's own dedicated LinkedIn account cookie from `settings` — isolated module, rate-limited, human-paced
- Normalizer job: `scrape_queue` -> `contacts`, only accepting publicly-listed emails, per user
- Confirm: run each scraper for a test user, verify rows land correctly and stay scoped to that user

## Step 10 — Context Matcher (DONE)
- Function: given a `contacts` row, return the best-matching `context_projects`/`context_experience` entry (same user) by tag overlap
- Confirm with test contacts before wiring in the LLM

## Step 11 — LLM Personalizer (DONE)
- Given a contact + matched context entry + chosen template (same user's version), call the LLM to fill dynamic placeholders
- Enforce: tone rule, ~120 word cap, no repeated hook phrasing across consecutive sends of the same template for the same user
- Confirm output against a few test contacts per test user, read them yourself before automating further

## Step 12 — Template Renderer (DONE)
- Merge static placeholders (from that user's `context_profile`) + dynamic placeholders (Step 11) into the template's `{{PLACEHOLDER}}` slots
- Output: final subject + body, stored against the contact, status -> `personalized`

## Step 13 — Send Queue + Scheduler (per user) (DONE)
- Rate limiter: 2-3 sends/hour per user within their configured window (default 08:00-23:00)
- Scheduler job iterates all active users each tick, respecting each one's `send_mode` and rate limit independently
- Confirm with `send_mode = review`: contacts pile up in `queued` without sending, for both test users independently; with `auto`, verify per-user pacing with a short test interval before trusting live 50/day timing

## Step 14 — SMTP Sender (per user) (DONE)
- Send function using each user's own SMTP creds from `settings`
- Wire into the scheduler from Step 13
- Log every send to `send_log` with `user_id`
- Confirm: send one real test email per test user, to themselves, before pointing at real contacts

## Step 15 — IMAP Reply/Bounce Tracker (per user) (DONE)
- Background job polling each user's inbox on an interval, using their own IMAP creds
- Match incoming mail to `send_log`, update that user's `contacts.status`
- Wire `auto_pause_on_signal` to pause only that user's queue, not everyone's
- Confirm: reply to a test send for one user, verify only their queue reacts

## Step 16 — Approval API (for `review` mode) (DONE)
- `GET /queue`, `POST /queue/{id}/approve`, `POST /queue/{id}/reject` — all scoped to the authenticated user
- Pure API, no frontend

## Step 17 — Deployment
- Deploy to Render/Railway free tier, connect to Neon/Supabase Postgres + storage bucket
- Confirm all app-level env vars are set in the hosting dashboard, not committed to the repo
- Run the full pipeline once end-to-end for one real user with `send_mode = review` before ever switching anyone to `auto`

## Step 18 — Stop here
- Do not build a frontend/UI in this pass. Wait for `design.md` before starting any frontend work.