# Cold Mail Automation — Project Spec

## 1. What this is
A hosted, multi-user tool that automates job-search cold outreach: each user scrapes public contacts, generates personalized emails from editable templates + their own dynamic context layer (projects/experience, built from their own uploaded resume), and sends them on a human-like schedule — without getting the sending account or the scraping account flagged/banned.

Each user signs up, uploads their resume, reviews the auto-filled context, and hits start — the system runs continuously in the background sending 2-3 emails/hour across the day, using that user's own SMTP account and templates.

## 2. Multi-tenant — every user has their own isolated data
Friends/other users will use this too, each with their own context, templates, contacts, and send queue. Every data table below is scoped by `user_id`. Nothing is shared across users except the application code itself:
- `users` (id, email, password_hash, created_at)
- `context_profile`, `context_experience`, `context_projects`, `context_achievements` — one set per user
- `resumes` — one or more per user
- `templates` — each user gets their own copy (seeded with 5 defaults on signup), fully editable, never shared
- `contacts`, `scrape_queue`, `send_log` — scoped per user
- `settings` (per user: SMTP creds, IMAP creds, send-mode, schedule window, LinkedIn scrape account creds)

No user can see or affect another user's data. Auth (JWT) on every route enforces `user_id` scoping at the query level, not just at the UI level.

## 3. Non-goals (explicitly out of scope for this build)
- No UI implementation yet. Backend exposes a clean REST API; a separate `design.md` will specify the frontend later. Do not invent UI/pages beyond minimal API-testable stubs.
- No email-guessing/pattern generation — only emails that are actually publicly listed are stored and used.
- No sending beyond each user's configured rate — the rate limiter is a hard per-user constraint, not a suggestion.

## 4. New: Resume-driven context onboarding
This replaces manually seeding the context layer. Flow, per user:
1. **Upload** — `POST /resume/upload` (PDF/doc), stored in object storage (see note below), row created in `resumes` table linked to `user_id`.
2. **Parse** — background job sends the resume text to the LLM with a strict prompt: "extract into this exact JSON schema" (the schema is `context_layer_seed.json`'s shape — `profile`, `experience[]`, `projects[]`, `achievements[]`, each entry tagged for the context-matcher).
3. **Fill** — parsed JSON is written into that user's `context_profile`/`context_experience`/`context_projects`/`context_achievements` rows automatically.
4. **Review/edit** — user can then edit any of it via the same CRUD API from the original spec — the LLM fill is a starting point, not a lock-in.

**Storage note / assumption flagged:** you said "store the resume in chrome storage" — for a hosted multi-user backend, the raw resume file needs to live in real persistent storage (a bucket — Supabase Storage or S3-compatible), keyed by `user_id`, since browser-local storage can't hold a shared server-side file across devices/sessions or survive being re-parsed by a background job. I've built the spec around a storage bucket. If you specifically meant storing a copy in the browser (e.g. for an offline/extension use case) that's an additive frontend concern for `design.md`, not a replacement for server-side storage — flag it there if so.

## 5. High-level architecture
```
[User uploads resume] -> [LLM Resume Parser] -> [Context Layer (per user)]
                                                        |
[Scrapers] -> [Contact Store (Postgres, per user)] -> [Context Matcher] -> [LLM Personalizer]
                                                                                  |
                                                                                  v
                                                                        [Template Renderer]
                                                                                  |
                                                                                  v
                                                                [Send Queue + Scheduler] -> [SMTP Sender (per user's own account)]
                                                                                  |
                                                                                  v
                                                                        [IMAP Reply/Bounce Tracker]
```

All components run as a single Python (FastAPI) backend with a background worker (APScheduler, one scheduled job per active user) and a Postgres database (Neon/Supabase). Deployed on Render/Railway free tier.

## 6. Core components

### 6.1 Context Layer (dynamic, per user)
Tables (all with `user_id` FK):
- `context_profile` (role_title, grad_year, portfolio_url, github_url, email)
- `context_experience` (id, user_id, title, dates, one_liner, stack[], tags[])
- `context_projects` (id, user_id, title, dates, one_liner, stack[], tags[], link, live_link, note)
- `context_achievements` (id, user_id, text)

API: `GET/POST/PUT/DELETE /context/experience`, `/context/projects`, `/context/achievements`, `/context/profile` — all scoped to the authenticated user.

Populated primarily via the resume-parse flow (Section 4), editable manually after.

Matching rule: when personalizing an email, match on `tags` overlap between the target job posting/recipient and that user's `context_projects`/`context_experience` entries — pick the single best-matching entry, not the most impressive one.

Tone rule (enforce in the LLM prompt): state what was built and what problem it solved, plainly — no superlatives, no stacking multiple achievements into one line, no "proud to have."

### 6.2 Scrapers (per user — each user scrapes/sends independently)
Sources, in order of build priority (safest/most stable first):
1. Company career pages (static/simple scraping, no auth needed)
2. GitHub / AngelList (public API where possible)
3. Job portals (Naukri, LinkedIn Jobs listings, Indeed)
4. LinkedIn — via each user's own dedicated new LinkedIn account (never their real profile). Slow, low-frequency, human-paced requests only. LinkedIn session/cookie stored per user in `settings`.

Each scraper writes into a shared `scrape_queue` table: `{user_id, source, raw_data, discovered_at, status}`. A normalizer job turns queue entries into `contacts` rows.

Only emails found as publicly listed text (bio, post, README, careers page) are accepted into `contacts.email`. No pattern-guessing anywhere in this pipeline.

### 6.3 Contacts store
Table: `contacts (id, user_id, name, company, role, source, job_posting_url, email, linkedin_url, discovered_at, status)`
`status`: `new -> personalized -> queued -> sent -> replied/bounced`

### 6.4 Templates (per user, editable)
Each user gets their own 5 template rows on signup (seeded from `templates.md`'s defaults: Recruiter/HR outreach, Referral ask, Direct tech lead pitch, Follow-up, Cold apply), then can edit freely — wording, add/remove categories, change placeholders.

Table: `templates (id, user_id, category, subject_template, body_template)`
API: full CRUD, scoped to the authenticated user.

### 6.5 LLM Personalizer
Input: one `contacts` row + matched `context_projects`/`context_experience` entry (same user) + the chosen template (same user's version).
Output: filled dynamic placeholders (`PERSONAL_HOOK`, `RELEVANT_PROJECT_LINE`, `WHY_THIS_COMPANY`, etc. per template).
Constraint: enforce the tone rule from 6.1, hard cap ~120 words for the full rendered email, never repeat the same `PERSONAL_HOOK` phrasing across consecutive emails using the same template for the same user.

### 6.6 Send Queue + Scheduler (per user)
Rate limiter: 2-3 sends/hour per user, randomized within a configurable daily window (default 08:00-23:00), targeting ~50/day per user.
Send-mode toggle (per user setting), three modes:
- `auto` — sends as soon as personalized and its turn in the schedule comes up
- `review` — queued, that user approves each one via API before it sends
- `auto_pause_on_signal` — sends automatically but pauses that user's queue if a bounce or reply is detected, until they resume

### 6.7 SMTP Sender (per user's own account)
Each user configures their own Gmail/Outlook SMTP + app password via `settings` (encrypted at rest, never in env vars now that it's multi-user). One send = one SMTP transaction, logged to `send_log (user_id, contact_id, template_id, sent_at, status, message_id)`.

### 6.8 IMAP Reply/Bounce Tracker
Background job polls each user's inbox via IMAP on an interval (their own IMAP creds from `settings`), matches incoming messages to `send_log.message_id`/thread, updates that user's `contacts.status` to `replied` or `bounced`.

### 6.9 Auth
Real multi-user auth now: signup/login, password hashing (bcrypt/argon2), JWT sessions. Every protected route resolves `user_id` from the token and scopes every DB query to it — this is the core security requirement of the whole pivot, test it explicitly (Step in build_steps.md).

## 7. Tech stack summary
- Backend: Python, FastAPI
- DB: PostgreSQL (Neon/Supabase)
- Object storage: Supabase Storage (or S3-compatible) for resume files
- Scheduler: APScheduler (in-process; one job loop iterates active users)
- Sender: smtplib (SMTP + app password, per user)
- Reply tracking: imaplib (per user)
- Hosting: Render or Railway free tier
- Scraping: requests/httpx + BeautifulSoup for static pages; Playwright only where JS rendering is unavoidable (LinkedIn)

## 8. Environment variables required (app-level only — no per-user secrets in env anymore)
`DATABASE_URL`, `STORAGE_BUCKET_URL`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, `JWT_SECRET`, `LLM_API_KEY`

Per-user secrets (SMTP/IMAP/LinkedIn creds) live encrypted in the `settings` table, entered by each user after signup — never in env vars, since this is now multi-user.

## 9. Reference files (attached separately, feed these in alongside this doc)
- `templates.md` — the 5 default template skeletons (used to seed every new user's `templates` rows)
- `context_layer_seed.json` — example of the exact JSON shape the resume-parser LLM step must output; use it to validate the parser, not to hand-seed a specific user's data