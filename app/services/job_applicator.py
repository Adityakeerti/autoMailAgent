"""
Application Agent — Step 42 & 45
Playwright-based form filler that applies to jobs using the user's live Chrome session.
Supports LinkedIn Easy Apply, Indeed, Naukri, Wellfound, and generic ATS forms.
Always uploads the user's latest resume PDF fresh — never relies on portal-cached copies.

Safety rails (Step 46):
  - Duplicate guard: skips if already-submitted application exists
  - CAPTCHA/OTP detection: marks manual_needed and moves on
  - Human-paced delays between all Playwright actions
  - Retry on transient failures (up to 2 retries)
"""
import asyncio
import datetime
import logging
import os
import random
import tempfile
from typing import Any, Dict, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import JobApplication, JobListing, Resume

logger = logging.getLogger("job_applicator")

# Portals temporarily blocked due to consecutive failures (in-memory, resets on restart)
_blocked_portals: Dict[str, datetime.datetime] = {}
BLOCK_DURATION_MINUTES = 30

# Selectors for CAPTCHA / OTP modals we want to detect
CAPTCHA_SELECTORS = [
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    "[class*='captcha']",
    "[id*='captcha']",
    "[class*='challenge']",
    "input[type='tel'][placeholder*='OTP']",
    "input[placeholder*='verification code']",
    "#otp-input",
]

# File upload input selectors (tried in order)
RESUME_UPLOAD_SELECTORS = [
    "input[type='file'][accept*='pdf']",
    "input[type='file'][accept*='.pdf']",
    "input[type='file']",
    "[data-testid*='resume'] input[type='file']",
    "#resume-upload",
    "input[name*='resume']",
    "input[name*='cv']",
]

# Submit button text patterns
SUBMIT_PATTERNS = [
    "submit application",
    "submit",
    "apply now",
    "apply",
    "send application",
    "complete application",
    "finish",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_portal_blocked(portal: str) -> bool:
    if portal not in _blocked_portals:
        return False
    blocked_until = _blocked_portals[portal] + datetime.timedelta(minutes=BLOCK_DURATION_MINUTES)
    if datetime.datetime.utcnow() < blocked_until:
        return True
    del _blocked_portals[portal]
    return False


def _increment_block(portal: str):
    """Mark a portal as temporarily blocked."""
    _blocked_portals[portal] = datetime.datetime.utcnow()
    logger.warning(f"Portal {portal} temporarily blocked for {BLOCK_DURATION_MINUTES} minutes.")


async def _human_pause(min_s: float = 1.0, max_s: float = 3.0):
    await asyncio.sleep(random.uniform(min_s, max_s))


async def _check_captcha(page) -> bool:
    """Returns True if a CAPTCHA/OTP challenge is detected on the current page."""
    for selector in CAPTCHA_SELECTORS:
        try:
            el = await page.query_selector(selector)
            if el:
                return True
        except Exception:
            pass
    return False


async def _upload_resume(page, resume_path: str) -> bool:
    """
    Attempts to upload the resume PDF to the first matching file input.
    Returns True on success.
    """
    for selector in RESUME_UPLOAD_SELECTORS:
        try:
            el = await page.query_selector(selector)
            if el:
                await el.set_input_files(resume_path)
                await _human_pause(1.0, 2.0)
                logger.info(f"Resume uploaded via selector: {selector}")
                return True
        except Exception as e:
            logger.debug(f"Resume upload failed for selector {selector}: {e}")
    return False


async def _fill_text_field(page, selectors: list, value: str):
    """Try each selector; fill the first found one."""
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                await el.fill(value)
                await _human_pause(0.3, 0.8)
                return True
        except Exception:
            pass
    return False


# ---------------------------------------------------------------------------
# Portal-specific fillers
# ---------------------------------------------------------------------------

async def _apply_linkedin(page, listing: JobListing, resume_path: str, profile_data: dict) -> str:
    """
    LinkedIn Easy Apply flow.
    Returns one of: submitted, already_applied, manual_needed, failed
    """
    try:
        await page.goto(listing.job_url, wait_until="domcontentloaded", timeout=30000)
        await _human_pause(2, 4)

        # Check for "Already Applied" banner
        already = await page.query_selector(".artdeco-inline-feedback--success, .jobs-s-apply__application-link")
        if already:
            text = await already.inner_text()
            if "applied" in text.lower():
                return "already_applied"

        # Click Easy Apply button
        easy_apply = await page.query_selector(".jobs-apply-button--top-card button, .jobs-s-apply button")
        if not easy_apply:
            easy_apply = await page.query_selector("button:has-text('Easy Apply')")
        if not easy_apply:
            return "failed"

        await easy_apply.click()
        await _human_pause(1.5, 3)

        if await _check_captcha(page):
            logger.warning(f"CAPTCHA detected on LinkedIn for {listing.job_url}")
            return "manual_needed"

        # Multi-step modal: iterate up to 8 steps
        for step in range(8):
            await _human_pause(0.8, 2)

            # Upload resume if file input present
            await _upload_resume(page, resume_path)

            # Fill phone if empty
            await _fill_text_field(
                page,
                ["input[name='phoneNumber'], input[id*='phone'], input[placeholder*='phone']"],
                profile_data.get("phone", "")
            )

            # Check for submit button
            submit_btn = await page.query_selector(
                "button[aria-label='Submit application'], button:has-text('Submit application')"
            )
            if submit_btn:
                await submit_btn.click()
                await _human_pause(2, 4)
                return "submitted"

            # Check for Next button
            next_btn = await page.query_selector(
                "button[aria-label='Continue to next step'], button:has-text('Next'), button:has-text('Review')"
            )
            if next_btn:
                await next_btn.click()
                await _human_pause(1, 2)
            else:
                break

        return "failed"

    except Exception as e:
        logger.error(f"LinkedIn apply error for {listing.job_url}: {e}")
        return "failed"


async def _apply_naukri(page, listing: JobListing, resume_path: str, profile_data: dict) -> str:
    """Naukri apply flow with OTP detection."""
    try:
        await page.goto(listing.job_url, wait_until="domcontentloaded", timeout=30000)
        await _human_pause(2, 4)

        if await _check_captcha(page):
            return "manual_needed"

        apply_btn = await page.query_selector("button#apply-button, button:has-text('Apply'), a:has-text('Apply')")
        if not apply_btn:
            return "failed"

        await apply_btn.click()
        await _human_pause(2, 3)

        # OTP / re-auth modal
        otp_field = await page.query_selector("input[placeholder*='OTP'], input[type='tel']")
        if otp_field:
            logger.warning(f"OTP required on Naukri for {listing.job_url}")
            return "manual_needed"

        await _upload_resume(page, resume_path)

        submit_btn = await page.query_selector("button:has-text('Submit'), button:has-text('Apply')")
        if submit_btn:
            await submit_btn.click()
            await _human_pause(2, 3)
            return "submitted"

        return "failed"

    except Exception as e:
        logger.error(f"Naukri apply error: {e}")
        return "failed"


async def _apply_wellfound(page, listing: JobListing, resume_path: str, profile_data: dict) -> str:
    """Wellfound 1-click or multi-step apply."""
    try:
        await page.goto(listing.job_url, wait_until="domcontentloaded", timeout=30000)
        await _human_pause(2, 4)

        if await _check_captcha(page):
            return "manual_needed"

        apply_btn = await page.query_selector(
            "button:has-text('Apply'), a:has-text('Apply now'), [data-test='applyButton']"
        )
        if not apply_btn:
            return "failed"

        await apply_btn.click()
        await _human_pause(1.5, 3)
        await _upload_resume(page, resume_path)

        # Fill cover letter if present
        cover_field = await page.query_selector("textarea[placeholder*='cover'], textarea[name*='cover']")
        if cover_field and profile_data.get("cover_line"):
            await cover_field.fill(profile_data["cover_line"])
            await _human_pause(0.5, 1)

        submit_btn = await page.query_selector("button:has-text('Submit'), button:has-text('Apply')")
        if submit_btn:
            await submit_btn.click()
            await _human_pause(2, 3)
            return "submitted"

        return "failed"

    except Exception as e:
        logger.error(f"Wellfound apply error: {e}")
        return "failed"


async def _apply_general(page, listing: JobListing, resume_path: str, profile_data: dict) -> str:
    """
    Generic ATS / company career page apply.
    Scans for a form, fills name + email, uploads resume, clicks submit.
    """
    try:
        await page.goto(listing.job_url, wait_until="domcontentloaded", timeout=30000)
        await _human_pause(2, 4)

        if await _check_captcha(page):
            return "manual_needed"

        # Fill name
        await _fill_text_field(
            page,
            ["input[name*='name'][type='text']", "input[placeholder*='name']", "input[id*='name']"],
            profile_data.get("full_name", "")
        )

        # Fill email
        await _fill_text_field(
            page,
            ["input[type='email']", "input[name*='email']", "input[placeholder*='email']"],
            profile_data.get("email", "")
        )

        # Upload resume
        uploaded = await _upload_resume(page, resume_path)
        if not uploaded:
            return "failed"

        # Find and click submit
        for pattern in SUBMIT_PATTERNS:
            submit_btn = await page.query_selector(f"button:has-text('{pattern}'), input[type='submit'][value*='{pattern}']")
            if submit_btn:
                await _human_pause(1, 2)
                await submit_btn.click()
                await _human_pause(2, 4)
                return "submitted"

        return "failed"

    except Exception as e:
        logger.error(f"Generic apply error for {listing.job_url}: {e}")
        return "failed"


# ---------------------------------------------------------------------------
# Resume sourcing
# ---------------------------------------------------------------------------

_resume_path_cache: Dict[int, str] = {}  # user_id → local path (per-cycle cache)
_resume_temp_files: list = []  # temp file paths to clean up


async def get_latest_resume_path(user_id: int, db: AsyncSession) -> Optional[str]:
    """
    Returns the local filesystem path of the user's latest resume PDF.
    Caches the path for the current apply cycle.
    """
    if user_id in _resume_path_cache:
        return _resume_path_cache[user_id]

    res = await db.execute(
        select(Resume)
        .where(Resume.user_id == user_id)
        .order_by(Resume.uploaded_at.desc())
        .limit(1)
    )
    resume = res.scalar_one_or_none()
    if not resume:
        return None

    file_url = resume.file_url
    if file_url.startswith("./storage_data") or os.path.exists(file_url):
        # Local storage
        path = file_url if os.path.isabs(file_url) else os.path.abspath(file_url)
        if os.path.exists(path):
            _resume_path_cache[user_id] = path
            return path
        return None

    # Cloud storage: download to temp file
    try:
        from app.services.storage import storage_service
        data = storage_service.get_resume_bytes(file_url)
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.write(data)
        tmp.close()
        _resume_temp_files.append(tmp.name)
        _resume_path_cache[user_id] = tmp.name
        return tmp.name
    except Exception as e:
        logger.warning(f"Could not download resume for user {user_id}: {e}")
        return None


def clear_resume_cache(user_id: Optional[int] = None):
    """Clean up cached resume paths and temp files after an apply cycle."""
    global _resume_temp_files
    if user_id is not None:
        _resume_path_cache.pop(user_id, None)
    else:
        _resume_path_cache.clear()
    for path in _resume_temp_files:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
    _resume_temp_files = []


# ---------------------------------------------------------------------------
# Main apply dispatcher
# ---------------------------------------------------------------------------

async def apply_to_job(
    user_id: int,
    job_listing_id: int,
    db: AsyncSession,
    browser,
    profile_data: dict,
) -> Dict[str, Any]:
    """
    Main entry point. Dispatches to the correct portal filler.
    Writes a JobApplication row and updates JobListing.status.
    Returns {application_status, error_msg}.

    Safety checks:
    - Duplicate guard (already submitted)
    - Portal block check
    - Retry on transient failures (up to 2)
    """
    # Load listing
    res = await db.execute(
        select(JobListing).where(
            JobListing.id == job_listing_id,
            JobListing.user_id == user_id,
        )
    )
    listing = res.scalar_one_or_none()
    if not listing:
        return {"application_status": "failed", "error_msg": "Listing not found"}

    # Duplicate guard
    dup_res = await db.execute(
        select(JobApplication).where(
            JobApplication.user_id == user_id,
            JobApplication.job_listing_id == job_listing_id,
            JobApplication.application_status == "submitted",
        )
    )
    if dup_res.scalar_one_or_none():
        logger.info(f"Duplicate: listing {job_listing_id} already submitted for user {user_id}")
        listing.status = "applied"
        await db.commit()
        return {"application_status": "already_applied", "error_msg": None}

    # Portal block check
    if _is_portal_blocked(listing.portal):
        return {
            "application_status": "failed",
            "error_msg": f"Portal {listing.portal} is temporarily blocked (anti-bot backoff).",
        }

    # Get resume
    resume_path = await get_latest_resume_path(user_id, db)
    if not resume_path:
        return {"application_status": "failed", "error_msg": "No resume found. Please upload a resume first."}

    # Open a new page in user's browser
    page = await browser.new_page()
    application_status = "failed"
    error_msg = None

    portal_consecutive_errors = 0

    for attempt in range(3):  # up to 2 retries
        try:
            if listing.portal == "linkedin":
                application_status = await _apply_linkedin(page, listing, resume_path, profile_data)
            elif listing.portal == "naukri":
                application_status = await _apply_naukri(page, listing, resume_path, profile_data)
            elif listing.portal == "wellfound":
                application_status = await _apply_wellfound(page, listing, resume_path, profile_data)
            else:
                # indeed / general / arbeitnow / ats_direct
                application_status = await _apply_general(page, listing, resume_path, profile_data)
            break  # success — exit retry loop
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Apply attempt {attempt + 1} failed for listing {job_listing_id}: {e}")
            if attempt < 2:
                await asyncio.sleep(5)
            portal_consecutive_errors += 1

    try:
        await page.close()
    except Exception:
        pass

    # Block portal if too many consecutive errors
    if portal_consecutive_errors >= 2:
        _increment_block(listing.portal)

    # Write JobApplication row
    app = JobApplication(
        user_id=user_id,
        job_listing_id=job_listing_id,
        portal=listing.portal,
        resume_version_url=resume_path,
        application_status=application_status,
        error_msg=error_msg,
    )
    db.add(app)

    # Update listing status
    if application_status == "submitted":
        listing.status = "applied"
        listing.applied_at = datetime.datetime.utcnow()
    elif application_status == "already_applied":
        listing.status = "applied"
    elif application_status == "manual_needed":
        listing.status = "scored"  # leave in queue for manual review
    else:
        listing.status = "applied"  # failed — still mark so we don't retry endlessly

    await db.commit()

    logger.info(
        f"Apply result for listing {job_listing_id} (user {user_id}): {application_status}"
    )
    return {"application_status": application_status, "error_msg": error_msg}
