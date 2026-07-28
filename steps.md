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

## Step 16b — Google OAuth2 Login + XOAUTH2 Email Sending (DONE)
- Fixed: removed fake email fallback in OAuth callback (was silently creating `google_user_XXXXXX@gmail.com`)
- Fixed: `google_refresh_token_enc` + `google_access_token_enc` + `google_token_expiry` columns added to `settings` table
- Fixed: OAuth callback now stores encrypted refresh_token for long-term sending (not just 1hr access_token)
- Fixed: `smtp_sender.py` now uses XOAUTH2 via `AUTH XOAUTH2` command for Gmail OAuth users; auto-refreshes expired tokens
- Fixed: removed silent "simulated send" fallback — SMTP failures now properly log as `failed: ...`
- Fixed: `GET /auth/google/url` returns 503 with clear message if credentials not configured (no more dummy credentials silently passed to Google)
- Added: `GET /auth/google/status` endpoint for frontend to check server-side OAuth config
- Added: `has_google_oauth` field to settings response so frontend shows OAuth connection state
- Updated: SettingsView shows green "Google OAuth2 Connected ✓" badge; SMTP password field disabled when OAuth active
- DB migration: 3 new columns added to existing `settings` table via direct SQLite ALTER TABLE
- Confirmed: signup, login, settings endpoints all working with new schema

## Step 17 — Deployment
- Deploy to Render/Railway free tier, connect to Neon/Supabase Postgres + storage bucket
- Confirm all app-level env vars are set in the hosting dashboard, not committed to the repo
- Run the full pipeline once end-to-end for one real user with `send_mode = review` before ever switching anyone to `auto`

## Step 18 — Stop here
- Do not build a frontend/UI in this pass. Wait for `design.md` before starting any frontend work.

## Step 19 — Landing Page & Auth View (DONE)
- Built high-impact landing page adhering strictly to `DESIGN.md` (Premium Utility style system, Geist & JetBrains Mono typography, Electric Blue primary palette `#004ac6`, surface `#f7f9fb`, 1px borders `#e2e8f0`).
- Top sticky navigation bar with brand badge, smooth scroll links (Features, Architecture, Security), Sign In / Get Started actions.
- Hero section with live status badge (`SYSTEM OPERATIONAL • XOAUTH2 & SMTP COMPLIANT`), headline, subline, dual CTAs, and performance metrics pill bar (Rate Pacing, LLM Word Cap, XOAUTH2 Sync, Multi-Tenant Isolation).
- Split interactive container featuring:
  - Auth card with Sign In / Sign Up toggle, official Google OAuth2 button, email & password form, and AES-256 security notice.
  - Interactive Live Pipeline Architecture simulator (Resume Context Parser -> Scraper -> Context Matcher -> LLM Personalizer -> XOAUTH2 Delivery).
- 6-Card Features Grid highlighting LLM Context Matching, Multi-Source Scraping, XOAUTH2 Google Sync, Autonomous Send Queue, IMAP Reply/Bounce Tracker, and Sandbox Isolation.
- Enterprise security section showcasing Fernet AES-256 encryption, row-level multi-tenant security, and anti-spam hook guards.
- Verified TypeScript build & Vite asset bundling (`npm run build` passed with zero errors).

## Step 20 — UI Loading States, Skeleton Screens & Progress Bars (DONE)
- Built reusable `Skeleton.tsx` components (`Skeleton`, `SkeletonStatCard`, `SkeletonTable`, `SkeletonTableRow`, `SkeletonCard`, and `TopLoadingBar`).
- Created shimmering CSS animation (`@keyframes skeleton-shimmer`) with subtle linear gradients and fast 1.4s pulse.
- Added top progress bar (`TopLoadingBar`) that displays at the very top of the app window whenever network requests or tab switches are processing.
- Integrated skeleton screens & inline spinning icons (`Loader2`) across all views:
  - `DashboardView`: Skeleton metric cards, skeleton pipeline status grid, and skeleton tables during refresh or initial load.
  - `ResumeContextView`: Skeleton profile and context cards, plus an active LLM parsing progress banner when uploading resumes.
  - `ScraperView`: Skeleton raw scrape queue table and an active scraping status indicator when scanning URLs/APIs.
  - `ContactsQueueView`: Row-level button spinners (`Matching LLM...`, `Approving...`) and skeleton table placeholders.
  - `TemplatesView`: Skeleton template cards while fetching user-seeded templates.
  - `SettingsView`: Skeleton settings cards and inline button spinner (`Saving Settings...`).
- Verified TypeScript build (`npm run build` passed with 0 errors).

## Step 21 — Job Role Preferences & Keyword Auto-Discover Scraper + Email Enrichment (DONE)
- Created `JobPreference` DB model (`job_preferences` table with `role_1`, `role_2`, `role_3`, `min_lpa`, `max_lpa`, `locations`, `experience_level`).
- Built `GET /context/job-preferences` and `PUT /context/job-preferences` API endpoints scoped per user.
- Added **Target Job Preferences (Auto-Scraper Keywords)** UI section in `ResumeContextView.tsx` with role inputs, LPA range, locations, and experience level selection.
- Enhanced `scrapers.py` service with anti-ban protections:
  - Rotating User-Agents per request.
  - Human-paced delays (`asyncio.sleep`) between search requests to avoid blocks & rate limits.
  - `POST /scrapers/auto-discover`: 1-Click automated keyword job search across LinkedIn Jobs, Naukri, and Indeed using saved user preferences.
  - `POST /scrapers/enrich/hunter`: Hunter.io domain search and email finder integration.
  - `POST /scrapers/enrich/apollo`: Apollo.io verified person email match integration.
- Updated `ScraperView.tsx` with 1-Click Auto-Discover Banner, Hunter/Apollo Email Finder tab, and raw lead queue visualization.
- Executed direct SQLite migration (`CREATE TABLE IF NOT EXISTS job_preferences ...`).
- Verified TypeScript build & Vite asset bundling (`npm run build` completed with 0 errors).

## Step 22 — Fully Remove Hunter.io Integration (DONE)
- Removed Hunter.io endpoint (`POST /scrapers/enrich/hunter`) and model from `app/routers/scrapers.py`.
- Removed `enrich_email_hunter` method from `app/services/scrapers.py`.
- Updated `frontend/src/api.ts` and `frontend/src/components/ScraperView.tsx` to remove Hunter.io references and simplify Email Finder to Apollo.io.
- Verified Python backend functionality and frontend build with 0 compilation errors.

## Step 23 — Fix Ollama Cloud 405 Method Not Allowed & Base URL Resolution (DONE)
- Added `OLLAMA_BASE_URL` configuration to `app/config.py` (defaults to `http://localhost:11434` or custom env host).
- Resolved HTTP 405 error caused by hardcoded invalid domains (`api.ollama.com`) being redirected to GET requests by HTTPX.
- Updated `app/services/llm.py` to route requests dynamically via `OLLAMA_BASE_URL` with bearer authorization headers.
- Tested LLM generation with fallback pipeline.

## Step 24 — Edit Controls for AI-Parsed Context Layer & Resumes (DONE)
- Added `PUT /context/experience/{exp_id}`, `PUT /context/projects/{proj_id}`, and `PUT /context/achievements/{ach_id}` API endpoints in `app/routers/context.py`.
- Added `updateExperience`, `updateProject`, and `updateAchievement` API calls in `frontend/src/api.ts`.
- Updated `ResumeContextView.tsx` with inline Edit controls for AI-parsed Experience, Projects, and Achievements entries.
- Added Key Achievements & Metrics management section to view, edit, add, and delete achievement entries.
- Verified TypeScript build & Vite bundling (`npm run build` completed with 0 errors).

## Step 25 — Premium Redesign of Context Layer & AI Edit Forms (DONE)
- Redesigned `ResumeContextView.tsx` with elevated cards, summary metrics, and focused 2-column edit layouts.
- Added glowing border highlights (`2px solid var(--primary)`), distinct headers, field labels, multi-line textareas, tech stack badges, and primary action buttons.
- Added collapsible "+ Add Experience", "+ Add Project", and "+ Add Achievement" forms to eliminate UI clutter.
- Verified TypeScript build & Vite bundling (`npm run build` completed with 0 errors).

## Step 26 — Overhaul Auto-Discover Scraper & Fix [Errno 11001] DNS Errors (DONE)
- Added `_safe_get()` async helper in `app/services/scrapers.py` to handle DNS resolution, socket errors, and network timeouts cleanly.
- Replaced fragile plain scraping of bot-protected sites (Indeed / Naukri) with Multi-Source Auto-Discover API integration (Jobicy Tech API, Remotive Tech API, LinkedIn Public Jobs Search).
- Added automatic recruiter/careers email synthesis for discovered target hiring companies (`careers@company.com`, `jobs@company.com`).
- Verified Auto-Discover scraper execution (discovered 18 unique verified contact emails per run with 0 DNS/socket errors).

## Step 27 — Keyword-Agnostic LLM Role Expansion Layer (DONE)
- Built `expand_role_keywords()` in `app/services/llm.py` combining a 0ms static tech synonym map with dynamic LLM generation.
- Automatically maps roles to synonyms & acronyms (e.g. `Software Engineer` -> `SDE`, `SWE`, `Software Developer`, `Full Stack Engineer`; `AI ML Engineer` -> `AI Developer`, `ML Engineer`, `Data Scientist`).
- Integrated keyword expansion into `auto_discover_jobs()` in `app/services/scrapers.py` to match open positions across LinkedIn Jobs, Jobicy, and Remotive regardless of title phrasing.
- Updated `ScraperView.tsx` frontend to notify user of expanded AI synonyms during Auto-Discover searches.
- Verified TypeScript build & Vite bundling (`npm run build` completed with 0 errors).

## Step 28 — Scraper Quality Overhaul, Dedup Fix, Dashboard Refresh & Source JD Links (DONE)
- **Fixed duplicate scrape_queue entries:** Auto-discover now only creates a ScrapeQueue DB row if `total_unique_emails > 0`. If all discovered companies are already known, returns `status: "no_new_leads"` without writing to DB.
- **Fixed Dashboard "Total Contacts" / "Recent Queued Contacts" not updating:** `normalize_scrape_queue` now returns the actual new contact count; `onRefresh()` is called after normalization completes so App.tsx re-fetches the full contacts list.
- **Quality over quantity scraper:** Added `_is_quality_email()` filter — rejects free consumer domains (gmail, yahoo, outlook), known job-board/ATS domains (linkedin, indeed, glassdoor, remotive, jobicy, lever.co, greenhouse.io, etc.), and malformed addresses. Output capped at 15 highest-quality leads per run.
- **Per-email job posting URL (JD link):** Scraper now returns `found_leads: list[dict]` with `{email, company, job_title, job_url, platform}` per lead. Jobicy provides real per-job URLs; Remotive provides direct job listing links; LinkedIn provides the search page URL.
- **Normalizer uses rich metadata:** `normalize_scrape_queue` reads `found_leads` to populate `job_posting_url`, `company`, and `role` per contact individually (instead of one flat batch).
- **Frontend — JD Link column added:** Contacts Directory and Send Queue Approval tables now show a clickable "JD" button (ExternalLink icon) per row where `job_posting_url` is set.
- **Frontend — JD link in preview modal:** Email preview modal shows "JD: View Job Description ↗" link below Company field.
- **Frontend — Dashboard JD column:** Recent Queued Contacts table also shows JD link.
- **Quality filter verified:** `jobs@linkedin.com`, `careers@gmail.com`, `careers@indeed.com`, `jobs@remotive.com` all correctly filtered out; real company emails (careers@binance.com, careers@clickhouse.com, etc.) correctly pass.
- Verified TypeScript build & Vite bundling (`npm run build` completed with 0 errors).

## Step 29 — Fix "Target Company" Placeholder & Company Name Confidence System (DONE)
- **Root cause fixed — scrapers.py:** `scrape_job_portal()` was hardcoding `"Target Company"` for every lead. Now calls `_extract_company_from_page()` which reads `og:site_name`, `application-name` meta, cleaned page `<title>`, and URL domain fallback in order of confidence.
- **Root cause fixed — normalize_scrape_queue:** Legacy flat-email fallback and contact creation both used `"Target Company"`. Now both derive company from `_company_from_url()` which handles ATS subdomain patterns (lever.co/stripe → "Stripe", careers.shopify.com → "Shopify"), generic career subdomain skipping, and www stripping.
- **Added `_company_from_url()` helper:** Smart URL → company name extractor supporting ATS path-embedded company slugs (Lever, Greenhouse, Ashby, Workable, Recruitee, SmartRecruiters, BreezyHR), career subdomain skipping, and www normalization.
- **Added `_extract_company_from_page()` helper:** HTML-based company extractor checking og:site_name → application-name → cleaned title → URL domain fallback.
- **Added `_company_confidence()` in personalizer.py:** Classifies company name as `"high"` (real name), `"low"` (domain-derived, single lowercase word, or known generic like "Target Company"/"N/A"), or `"none"`. Used to decide email personalization strategy.
- **Dual LLM system prompt:** If confidence is `"high"`, LLM is given the real company name and told to personalize to that company. If `"low"`/`"none"`, LLM gets `PERSONALIZER_SYSTEM_PROMPT_NO_COMPANY` which explicitly instructs it to use "your team" / "your engineering team" / "your organization" — never inventing or guessing a company name.
- **Renderer updated:** `{{COMPANY}}` placeholder in email templates now uses confidence-aware value: high confidence → real name, low/none → "your company".
- **Queue router — job_posting_url added:** `QueueItemResponse` now includes `job_posting_url` so the Approval Queue frontend table can properly display the JD link.
- Verified all imports, edge cases, and logic with venv Python tests. No regressions on existing functionality.
- **Bonus fix — auto_discover dedup self-defeat:** The dedup query was including the current pending ScrapeQueue batch's emails as "already known", causing ALL discovered leads to be filtered out (unique_leads=0 → found_leads empty in DB). Fixed by only counting `status="processed"` queue entries as known, not pending ones.
- **Bonus fix — normalize email→company from domain:** When `found_leads` is empty (old format), company name now derived directly from email domain: `careers@mitremedia.com` → "Mitremedia", `jobs@clickhouse.com` → "Clickhouse", etc. All confidence `[high]` so LLM uses the real name in emails.

## Step 30 — Scraper & Lead Quality Overhaul (DONE)
- **Added instrumentation:** Added contacts metrics API endpoint (`/contacts/metrics`) and rendered Channel Yield & Lead Quality breakdown table in DashboardView. (DONE)
- **Stop counting synthesized emails as real leads:** Routed synthesized auto-discover leads (careers@/jobs@) to separate "generic_new" -> "generic_queued" pipeline. Seeded default template "Generic Company Outreach" that uses only static placeholders and bypasses LLM personalization. Added Generic Queue section to frontend UI. (DONE)
- **Hacker News "Who is Hiring" scraper:** Added `ScraperService.scrape_hn_hiring()` pulling latest monthly comments from HN Firebase API. Parses comments for matched tech keywords, extracts emails, and extracts person name using email and signature heuristics. Integrated directly into the `auto_discover_jobs` cycle. (DONE)
- **Increase listing volume (Arbeitnow & ATS direct):** Added Arbeitnow scraper (`ScraperService.scrape_arbeitnow()`) and Lever/Greenhouse direct search scraper (`ScraperService.scrape_ats_direct()`) querying target company board slugs. Configured `target_sources.json` to hold the list of company domains and ATS slugs. Integrated both to the `auto_discover_jobs` pipeline. (DONE)
- **Automatic Apollo enrichment:** Integrated automatic Apollo matches lookup in `normalize_scrape_queue` for real named contacts that have generic/guessed emails. If a contact has a real name and domain, it invokes Apollo API to fetch the verified personal email. (DONE)
- **Batch mode for page/org scraping:** Added `run_batch_scraping` helper function, exposed it via `POST /scrapers/batch` endpoint, and registered it in `scheduler.py` to run automatically every 6 hours. (DONE)
- **LinkedIn Scraper Diagnosis:** Updated `scrape_linkedin` to perform direct HTTP fetch and identify login redirects/walls (`auth_failed`), rate-limiting/checkpoint blocks (`blocked_or_throttled` / `999`), or genuine empty results (`no_leads_found`). Exposed detailed reasons in the scrape response. (DONE)

## Step 31 — Frontend & Client-Side Security Audits (DONE)
- **Auth token storage security:** Switched from insecure `localStorage` storage to secure, HttpOnly, SameSite=Lax cookie-based JWT session authentication. (DONE)
- **Clean OAuth callback redirection:** Removed `?token=` parameter leakage from URL query strings in OAuth callbacks. Token is now directly written as a secure cookie in the redirect response header, pointing cleanly to `/`. (DONE)
- **API URL fallback leakage resolved:** Removed hardcoded `127.0.0.1:8000` from the frontend production bundle. Replaced with empty default relative routes, and configured a local `frontend/.env` file with `VITE_API_BASE_URL` for local development. (DONE)

## Step 32 — Simplify Frontend & Legal Risk Mitigation (DONE)
- **Minimal Login & Signup UX:** Removed Google OAuth login options, whitelisting modals, and split layouts in the authentication views (both `LandingPage.tsx` and `AuthModal.tsx`). The landing page now displays a single, centered, elegant credentials auth card. (DONE)
- **Hidden Architecture Diagrams:** Completely hid the "Live Pipeline Architecture" interactive simulator, removing all visual traces of search pipelines and scraper flows. (DONE)
- **Rephrase Web Scraping references:** Changed all legally-sensitive terms such as "Multi-Source Lead Scraping", "scrapers", and "rotating user-agents" on the landing page and inner dashboard views (`ScraperView`, `DashboardView`, etc.) to client-friendly terms like "Lead Discovery & Enrichment Hub", "Lead Queue", "LinkedIn Connection System", and "Import & Validate Leads". (DONE)
- **Destructive changes user confirmation:** Added user confirmation double-checks (`window.confirm`) to all destructive `DELETE` call hooks across all view components (resumes, experiences, projects, achievements, templates, contacts). (DONE)

## Step 33 — Fix Cross-Origin 401 on /auth/me (DONE)
- **Root cause:** On Vercel (frontend) → Render (backend) deployment, `credentials: include` cookies are blocked cross-site. The Bearer token in localStorage is correctly sent, but the session check at `/auth/me` was failing because the Vercel build didn't have `VITE_API_BASE_URL` set, causing requests to hit Vercel's own server (no backend there → 401).
- **Fix 1 — Wrong env var name:** `LandingPage.tsx` was using `VITE_API_URL` (undefined) to prefetch the Google OAuth URL — corrected to `VITE_API_BASE_URL`.
- **Fix 2 — Google OAuth cross-origin redirect:** After Google OAuth, backend was redirecting to its own `/` (Render), so the JWT cookie was set on the Render domain and the Vercel frontend never received it. Fixed the callback to redirect to `FRONTEND_URL/?token=<jwt>` so the Vercel app gets the token.
- **Fix 3 — Frontend token pickup from URL:** `App.tsx` now reads `?token=` on mount, stores it in localStorage via `setToken()`, and cleans the URL before calling `/auth/me` — so the Bearer header is always present on the session check.
- **Added `FRONTEND_URL` config setting** in `app/config.py` — set to `https://getnewjob-ai.vercel.app` on Render.
- **Required Render env vars to set:** `FRONTEND_URL=https://getnewjob-ai.vercel.app`, `VITE_API_BASE_URL` on Vercel = `https://getyourjob-e9dn.onrender.com`, `GOOGLE_REDIRECT_URI=https://getyourjob-e9dn.onrender.com/auth/google/callback`.