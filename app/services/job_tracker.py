"""
Tracking Agent + Run Orchestrator — Steps 43 & 46
Wires Search → Filter → Apply into one full pipeline run.
Manages the semi-auto approval queue, daily cap, and stats.
"""
import asyncio
import datetime
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import JobApplication, JobListing, JobPreference, ContextProfile

logger = logging.getLogger("job_tracker")


# ---------------------------------------------------------------------------
# Approval queue helpers
# ---------------------------------------------------------------------------

async def get_approval_queue(user_id: int, db: AsyncSession) -> List[Dict[str, Any]]:
    """Return all 'scored' listings (semi-auto approval queue)."""
    res = await db.execute(
        select(JobListing)
        .where(JobListing.user_id == user_id, JobListing.status == "scored")
        .order_by(JobListing.match_score.desc().nullslast(), JobListing.discovered_at.desc())
    )
    listings = res.scalars().all()
    return [_listing_to_dict(l) for l in listings]


async def approve_listing(user_id: int, listing_id: int, db: AsyncSession) -> Dict[str, Any]:
    """Approve a listing — sets status to 'approved'."""
    res = await db.execute(
        select(JobListing).where(
            JobListing.id == listing_id, JobListing.user_id == user_id
        )
    )
    listing = res.scalar_one_or_none()
    if not listing:
        return {"error": "Listing not found"}
    listing.status = "approved"
    await db.commit()
    return {"id": listing_id, "status": "approved"}


async def reject_listing(user_id: int, listing_id: int, db: AsyncSession, reason: str = "") -> Dict[str, Any]:
    """Reject a listing — sets status to 'skipped'."""
    res = await db.execute(
        select(JobListing).where(
            JobListing.id == listing_id, JobListing.user_id == user_id
        )
    )
    listing = res.scalar_one_or_none()
    if not listing:
        return {"error": "Listing not found"}
    listing.status = "skipped"
    if reason:
        listing.match_reason = f"[Rejected] {reason}"
    await db.commit()
    return {"id": listing_id, "status": "skipped", "reason": reason}


# ---------------------------------------------------------------------------
# Apply cycle
# ---------------------------------------------------------------------------

async def run_apply_cycle(
    user_id: int,
    db: AsyncSession,
    browser,
) -> Dict[str, Any]:
    """
    Iterate all 'approved' listings and apply to each.
    Respects the daily cap from JobPreference.max_applications_per_day.
    Returns summary stats.
    """
    from app.services.job_applicator import apply_to_job, clear_resume_cache

    # Load preferences for daily cap
    jp_res = await db.execute(select(JobPreference).where(JobPreference.user_id == user_id))
    jp = jp_res.scalar_one_or_none()
    daily_cap = jp.max_applications_per_day if jp else 20

    # Load profile for form filling
    profile_res = await db.execute(
        select(ContextProfile).where(ContextProfile.user_id == user_id)
    )
    profile = profile_res.scalar_one_or_none()
    profile_data = {
        "full_name": (profile.full_name or "") if profile else "",
        "email": (profile.email or "") if profile else "",
        "phone": "",
        "cover_line": f"I'd love to contribute to your team as a {jp.role_1 if jp else 'Software Engineer'}.",
    }

    # Count today's applications
    today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    count_res = await db.execute(
        select(func.count(JobApplication.id)).where(
            JobApplication.user_id == user_id,
            JobApplication.application_status == "submitted",
            JobApplication.applied_at >= today_start,
        )
    )
    applied_today = count_res.scalar() or 0

    if applied_today >= daily_cap:
        return {
            "applied": 0,
            "failed": 0,
            "manual_needed": 0,
            "already_applied": 0,
            "skipped": 0,
            "stopped_reason": "daily_cap_reached",
            "daily_cap": daily_cap,
            "applied_today": applied_today,
        }

    # Fetch approved listings
    res = await db.execute(
        select(JobListing)
        .where(JobListing.user_id == user_id, JobListing.status == "approved")
        .order_by(JobListing.match_score.desc().nullslast(), JobListing.discovered_at.asc())
    )
    listings = res.scalars().all()

    stats = {
        "applied": 0,
        "failed": 0,
        "manual_needed": 0,
        "already_applied": 0,
        "skipped": 0,
        "stopped_reason": None,
    }

    try:
        for listing in listings:
            remaining_quota = daily_cap - applied_today - stats["applied"]
            if remaining_quota <= 0:
                stats["stopped_reason"] = "daily_cap_reached"
                break

            result = await apply_to_job(
                user_id=user_id,
                job_listing_id=listing.id,
                db=db,
                browser=browser,
                profile_data=profile_data,
            )
            status = result.get("application_status", "failed")
            if status == "submitted":
                stats["applied"] += 1
            elif status == "failed":
                stats["failed"] += 1
            elif status == "manual_needed":
                stats["manual_needed"] += 1
            elif status == "already_applied":
                stats["already_applied"] += 1
            else:
                stats["skipped"] += 1

            # Human-pace delay between applications
            await asyncio.sleep(random.uniform(2.0, 5.0))
    finally:
        clear_resume_cache(user_id)

    return stats


# ---------------------------------------------------------------------------
# Full pipeline run
# ---------------------------------------------------------------------------

async def full_pipeline_run(user_id: int, db: AsyncSession) -> Dict[str, Any]:
    """
    Orchestrates the complete pipeline:
      1. Job Search (run_job_search)
      2. Score all new listings (score_all_new_listings)
      3. Apply cycle (run_apply_cycle) — only if browser is available

    Returns a comprehensive summary dict.
    """
    from app.services.job_search import run_job_search
    from app.services.job_filter import score_all_new_listings
    from app.services.browser import get_cdp_browser, BrowserNotAvailableError

    summary: Dict[str, Any] = {
        "searched": 0,
        "new_listings": 0,
        "scored": 0,
        "auto_approved": 0,
        "queued_for_review": 0,
        "applied": 0,
        "failed": 0,
        "manual_needed": 0,
        "already_applied": 0,
        "skipped": 0,
        "daily_cap_hit": False,
        "browser_unavailable": False,
        "errors": [],
    }

    # Step 1: Search
    try:
        search_result = await run_job_search(user_id, db)
        if "error" in search_result:
            summary["errors"].append(f"Search: {search_result['error']}")
        else:
            summary["searched"] = len(search_result.get("portals_hit", []))
            summary["new_listings"] = search_result.get("new", 0)
    except Exception as e:
        logger.error(f"Job search error for user {user_id}: {e}")
        summary["errors"].append(f"Search exception: {e}")

    # Step 2: Score
    try:
        score_result = await score_all_new_listings(user_id, db)
        summary["scored"] = score_result.get("scored", 0)
        summary["auto_approved"] = score_result.get("auto_approved", 0)
        summary["queued_for_review"] = score_result.get("queued_for_review", 0)
    except Exception as e:
        logger.error(f"Scoring error for user {user_id}: {e}")
        summary["errors"].append(f"Score exception: {e}")

    # Step 3: Apply (requires live browser)
    try:
        from app.models import Setting
        res_settings = await db.execute(select(Setting).where(Setting.user_id == user_id))
        st = res_settings.scalar_one_or_none()
        port = st.browser_cdp_port if (st and st.browser_cdp_port) else 9222
        b_type = st.browser_type if (st and st.browser_type) else "brave"

        async with get_cdp_browser(port=port, browser_type=b_type) as browser:
            apply_result = await run_apply_cycle(user_id, db, browser)
            summary["applied"] = apply_result.get("applied", 0)
            summary["failed"] = apply_result.get("failed", 0)
            summary["manual_needed"] = apply_result.get("manual_needed", 0)
            summary["already_applied"] = apply_result.get("already_applied", 0)
            summary["skipped"] = apply_result.get("skipped", 0)
            summary["daily_cap_hit"] = apply_result.get("stopped_reason") == "daily_cap_reached"
    except BrowserNotAvailableError as e:
        summary["browser_unavailable"] = True
        summary["errors"].append(f"Browser: {e}")
    except Exception as e:
        logger.error(f"Apply cycle error for user {user_id}: {e}")
        summary["errors"].append(f"Apply exception: {e}")

    logger.info(f"Full pipeline run for user {user_id}: {summary}")
    return summary


# ---------------------------------------------------------------------------
# Stats & history helpers
# ---------------------------------------------------------------------------

async def get_job_stats(user_id: int, db: AsyncSession) -> Dict[str, Any]:
    """Aggregate stats for the job application dashboard."""
    # Total applied
    total_res = await db.execute(
        select(func.count(JobApplication.id)).where(
            JobApplication.user_id == user_id,
            JobApplication.application_status == "submitted",
        )
    )
    total_applied = total_res.scalar() or 0

    # This week
    week_start = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    week_res = await db.execute(
        select(func.count(JobApplication.id)).where(
            JobApplication.user_id == user_id,
            JobApplication.application_status == "submitted",
            JobApplication.applied_at >= week_start,
        )
    )
    week_applied = week_res.scalar() or 0

    # By portal
    portal_res = await db.execute(
        select(JobApplication.portal, func.count(JobApplication.id))
        .where(
            JobApplication.user_id == user_id,
            JobApplication.application_status == "submitted",
        )
        .group_by(JobApplication.portal)
    )
    by_portal = {portal: count for portal, count in portal_res.all()}

    # By status
    status_res = await db.execute(
        select(JobApplication.application_status, func.count(JobApplication.id))
        .where(JobApplication.user_id == user_id)
        .group_by(JobApplication.application_status)
    )
    by_status = {status: count for status, count in status_res.all()}

    # Queued for review count
    review_res = await db.execute(
        select(func.count(JobListing.id)).where(
            JobListing.user_id == user_id,
            JobListing.status == "scored",
        )
    )
    queued_for_review = review_res.scalar() or 0

    return {
        "total_applied": total_applied,
        "applied_this_week": week_applied,
        "by_portal": by_portal,
        "by_status": by_status,
        "queued_for_review": queued_for_review,
    }


async def get_job_errors(user_id: int, db: AsyncSession) -> List[Dict[str, Any]]:
    """Return failed and manual_needed applications with error messages."""
    res = await db.execute(
        select(JobApplication, JobListing)
        .join(JobListing, JobApplication.job_listing_id == JobListing.id)
        .where(
            JobApplication.user_id == user_id,
            JobApplication.application_status.in_(["failed", "manual_needed"]),
        )
        .order_by(JobApplication.applied_at.desc())
    )
    rows = res.all()
    return [
        {
            "id": app.id,
            "job_listing_id": app.job_listing_id,
            "job_title": listing.job_title,
            "company": listing.company,
            "portal": app.portal,
            "application_status": app.application_status,
            "error_msg": app.error_msg,
            "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            "job_url": listing.job_url,
        }
        for app, listing in rows
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _listing_to_dict(l: JobListing) -> Dict[str, Any]:
    return {
        "id": l.id,
        "portal": l.portal,
        "job_title": l.job_title,
        "company": l.company,
        "location": l.location,
        "job_url": l.job_url,
        "match_score": l.match_score,
        "match_reason": l.match_reason,
        "recommended_angle": l.recommended_angle,
        "status": l.status,
        "discovered_at": l.discovered_at.isoformat() if l.discovered_at else None,
        "applied_at": l.applied_at.isoformat() if l.applied_at else None,
    }


import random  # imported at bottom to avoid shadowing builtins at top
