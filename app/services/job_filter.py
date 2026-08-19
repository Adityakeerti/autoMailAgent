"""
Job Filter Agent — Step 40
Scores each 'new' job listing against the user's full context layer using the LLM.
Produces a 0-100 match_score, human-readable reason, and recommended_angle.
High-scoring listings (>= auto_apply_threshold) are auto-approved.
"""
import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ContextAchievement,
    ContextExperience,
    ContextProfile,
    ContextProject,
    JobListing,
    JobPreference,
)
from app.services.llm import llm_service

logger = logging.getLogger("job_filter")

JOB_SCORER_SYSTEM_PROMPT = """You are a precise job-fit evaluator.
Given a job description and a candidate's profile, you return a JSON object with EXACTLY these keys:
  "score"             : integer 0-100 (how well the candidate matches the job)
  "reason"            : string ≤200 chars (plain English explanation of the score)
  "recommended_angle" : string ≤100 chars (the strongest selling point for cover letter / application)

Scoring rules:
- 90-100: Candidate is an excellent match; skills, level, and role align perfectly.
- 70-89:  Good match; minor gaps.
- 50-69:  Partial match; significant gaps but relevant experience.
- 0-49:   Poor match; role or level misaligned.

Output ONLY the JSON object, nothing else."""


async def score_job(user_id: int, job_listing_id: int, db: AsyncSession) -> Dict[str, Any]:
    """
    Score a single job listing against the user's context layer.
    Updates the listing's match_score, match_reason, recommended_angle, and status.
    Returns {score, reason, recommended_angle, status_set}.
    """
    # Load the listing
    res = await db.execute(
        select(JobListing).where(
            JobListing.id == job_listing_id,
            JobListing.user_id == user_id,
        )
    )
    listing = res.scalar_one_or_none()
    if not listing:
        return {"error": f"JobListing {job_listing_id} not found for user {user_id}"}

    # Load user context
    profile_res = await db.execute(
        select(ContextProfile).where(ContextProfile.user_id == user_id)
    )
    profile = profile_res.scalar_one_or_none()

    exp_res = await db.execute(
        select(ContextExperience).where(ContextExperience.user_id == user_id)
    )
    experiences = exp_res.scalars().all()

    proj_res = await db.execute(
        select(ContextProject).where(ContextProject.user_id == user_id)
    )
    projects = proj_res.scalars().all()

    ach_res = await db.execute(
        select(ContextAchievement).where(ContextAchievement.user_id == user_id)
    )
    achievements = ach_res.scalars().all()

    jp_res = await db.execute(
        select(JobPreference).where(JobPreference.user_id == user_id)
    )
    jp = jp_res.scalar_one_or_none()

    # Build context string
    profile_lines = []
    if profile:
        profile_lines.append(f"Name: {profile.full_name or 'N/A'}")
        profile_lines.append(f"Current role: {profile.role_title or 'N/A'}")
        profile_lines.append(f"Grad year: {profile.grad_year or 'N/A'}")

    exp_lines = []
    for e in experiences:
        exp_lines.append(f"- {e.title} ({e.dates or 'N/A'}): {e.one_liner or ''} | Stack: {', '.join(e.stack or [])}")

    proj_lines = []
    for p in projects:
        proj_lines.append(f"- {p.title}: {p.one_liner or ''} | Stack: {', '.join(p.stack or [])}")

    ach_lines = [f"- {a.text}" for a in achievements]

    pref_lines = []
    if jp:
        pref_lines.append(f"Target roles: {', '.join(r for r in [jp.role_1, jp.role_2, jp.role_3] if r)}")
        pref_lines.append(f"Locations: {jp.locations or 'Any'}")
        pref_lines.append(f"Experience level: {jp.experience_level or 'Entry'}")

    candidate_ctx = "\n".join([
        "=== CANDIDATE PROFILE ===",
        *profile_lines,
        "",
        "=== EXPERIENCE ===",
        *exp_lines,
        "",
        "=== PROJECTS ===",
        *proj_lines,
        "",
        "=== ACHIEVEMENTS ===",
        *ach_lines,
        "",
        "=== JOB PREFERENCES ===",
        *pref_lines,
    ])

    job_ctx = "\n".join([
        "=== JOB LISTING ===",
        f"Title: {listing.job_title}",
        f"Company: {listing.company or 'N/A'}",
        f"Location: {listing.location or 'N/A'}",
        f"Portal: {listing.portal}",
        f"URL: {listing.job_url}",
        "",
        "Description:",
        listing.description_raw or "(no description available)",
    ])

    prompt = f"{candidate_ctx}\n\n{job_ctx}\n\nReturn the JSON score object now."

    # Call LLM
    try:
        raw = await llm_service.generate_text(
            prompt=prompt,
            system_prompt=JOB_SCORER_SYSTEM_PROMPT,
            high_tier=False,
            json_mode=True,
        )
        data = json.loads(raw)
        score = int(data.get("score", 0))
        reason = str(data.get("reason", ""))[:200]
        angle = str(data.get("recommended_angle", ""))[:100]
    except Exception as e:
        logger.warning(f"LLM scoring failed for listing {job_listing_id}: {e}")
        score = 0
        reason = "Scoring failed — will land in review queue."
        angle = ""

    # Determine auto-apply threshold
    threshold = 90
    if jp and jp.auto_apply_threshold:
        threshold = jp.auto_apply_threshold

    new_status = "approved" if score >= threshold else "scored"

    # Write back to DB
    listing.match_score = float(score)
    listing.match_reason = reason
    listing.recommended_angle = angle
    listing.status = new_status
    await db.commit()

    logger.info(
        f"Scored listing {job_listing_id} for user {user_id}: "
        f"score={score}, status={new_status}"
    )
    return {
        "listing_id": job_listing_id,
        "score": score,
        "reason": reason,
        "recommended_angle": angle,
        "status_set": new_status,
    }


async def score_all_new_listings(user_id: int, db: AsyncSession) -> Dict[str, Any]:
    """
    Score all 'new' job listings for the user.
    Returns summary: {scored, auto_approved, queued_for_review}.
    """
    res = await db.execute(
        select(JobListing).where(
            JobListing.user_id == user_id,
            JobListing.status == "new",
        )
    )
    listings = res.scalars().all()

    scored = 0
    auto_approved = 0
    queued_for_review = 0

    for listing in listings:
        try:
            result = await score_job(user_id, listing.id, db)
            if "error" not in result:
                scored += 1
                if result["status_set"] == "approved":
                    auto_approved += 1
                else:
                    queued_for_review += 1
        except Exception as e:
            logger.error(f"Error scoring listing {listing.id}: {e}")

    return {
        "scored": scored,
        "auto_approved": auto_approved,
        "queued_for_review": queued_for_review,
    }
