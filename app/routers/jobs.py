"""
Jobs Router — Steps 39-43 & 46
Exposes all Job Application Agent endpoints.
All routes are scoped to the authenticated user via the JWT middleware.
"""
import math
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import JobApplication, JobListing, User, Setting
from app.security import get_current_user

router = APIRouter(prefix="/jobs", tags=["jobs"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class BrowserConfigRequest(BaseModel):
    browser_type: str
    browser_cdp_port: Optional[int] = 9222
    browser_custom_path: Optional[str] = None


class JobListingResponse(BaseModel):
    id: int
    portal: str
    job_title: str
    company: Optional[str] = None
    location: Optional[str] = None
    job_url: str
    match_score: Optional[float] = None
    match_reason: Optional[str] = None
    recommended_angle: Optional[str] = None
    status: str
    discovered_at: Optional[str] = None
    applied_at: Optional[str] = None

    class Config:
        from_attributes = True


class JobApplicationResponse(BaseModel):
    id: int
    job_listing_id: int
    portal: str
    resume_version_url: Optional[str] = None
    application_status: str
    error_msg: Optional[str] = None
    applied_at: Optional[str] = None

    class Config:
        from_attributes = True


class ApproveRejectRequest(BaseModel):
    reason: Optional[str] = ""


# ---------------------------------------------------------------------------
# Step 39: Job Search
# ---------------------------------------------------------------------------

@router.post("/search")
async def search_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger job search across all portals and store new listings."""
    from app.services.job_search import run_job_search
    result = await run_job_search(current_user.id, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/listings")
async def get_job_listings(
    status: Optional[str] = Query(None, description="Filter by status: new/scored/approved/applied/skipped"),
    portal: Optional[str] = Query(None, description="Filter by portal"),
    match_score_min: Optional[float] = Query(None, description="Minimum match score"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Paginated list of job listings with optional filters."""
    query = select(JobListing).where(JobListing.current_user.id == current_user.id)
    if status:
        query = query.where(JobListing.status == status)
    if portal:
        query = query.where(JobListing.portal == portal)
    if match_score_min is not None:
        query = query.where(JobListing.match_score >= match_score_min)

    # Total count
    count_q = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_q)
    total = total_res.scalar() or 0

    # Paginated results
    offset = (page - 1) * page_size
    query = query.order_by(JobListing.discovered_at.desc()).offset(offset).limit(page_size)
    res = await db.execute(query)
    listings = res.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 1,
        "listings": [_listing_to_dict(l) for l in listings],
    }


@router.get("/listings/{listing_id}")
async def get_job_listing(
    listing_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detailed view of a single job listing."""
    res = await db.execute(
        select(JobListing).where(
            JobListing.id == listing_id,
            JobListing.current_user.id == current_user.id,
        )
    )
    listing = res.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return _listing_to_dict(listing, include_description=True)


# ---------------------------------------------------------------------------
# Step 40: Job Filter / Scorer
# ---------------------------------------------------------------------------

@router.post("/score")
async def score_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Score all 'new' listings using the LLM filter agent."""
    from app.services.job_filter import score_all_new_listings
    result = await score_all_new_listings(current_user.id, db)
    return result


# ---------------------------------------------------------------------------
# Step 41 & 47: Browser / portal login detection & launcher config
# ---------------------------------------------------------------------------

@router.get("/browser/status")
async def get_browser_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Check if the user's selected browser is reachable via CDP and which portals they are logged in.
    Reads browser settings from user settings.
    """
    from app.services.browser import get_browser_status as check_status
    res = await db.execute(select(Setting).where(Setting.user_id == current_user.id))
    st = res.scalar_one_or_none()
    
    port = st.browser_cdp_port if (st and st.browser_cdp_port) else 9222
    b_type = st.browser_type if (st and st.browser_type) else "brave"
    custom_path = st.browser_custom_path if st else None
    
    return await check_status(port=port, browser_type=b_type, custom_path=custom_path)


@router.post("/browser/launch")
async def launch_browser(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Automatically search default paths and launch the configured browser
    with the debugging port active.
    """
    from app.services.browser import launch_browser_instance
    res = await db.execute(select(Setting).where(Setting.user_id == current_user.id))
    st = res.scalar_one_or_none()
    
    port = st.browser_cdp_port if (st and st.browser_cdp_port) else 9222
    b_type = st.browser_type if (st and st.browser_type) else "brave"
    custom_path = st.browser_custom_path if st else None
    
    result = launch_browser_instance(browser_type=b_type, port=port, custom_path=custom_path)
    if not result.get("success"):
        # We still return 200 with the payload so the frontend can display commands
        return result
    return result


@router.put("/browser/config")
async def update_browser_config(
    data: BrowserConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update browser selection, CDP port, and optional custom executable path.
    """
    res = await db.execute(select(Setting).where(Setting.user_id == current_user.id))
    st = res.scalar_one_or_none()
    if not st:
        st = Setting(user_id=current_user.id)
        db.add(st)

    valid_browsers = ["brave", "chrome", "edge", "custom"]
    if data.browser_type.lower() not in valid_browsers:
        raise HTTPException(status_code=400, detail=f"Invalid browser_type. Must be one of: {', '.join(valid_browsers)}")

    st.browser_type = data.browser_type.lower()
    
    if data.browser_cdp_port is not None:
        if data.browser_cdp_port < 1024 or data.browser_cdp_port > 65535:
            raise HTTPException(status_code=400, detail="CDP port must be between 1024 and 65535.")
        st.browser_cdp_port = data.browser_cdp_port
        
    if data.browser_custom_path is not None:
        st.browser_custom_path = data.browser_custom_path

    await db.commit()
    await db.refresh(st)
    
    from app.services.browser import get_browser_status as check_status
    return await check_status(port=st.browser_cdp_port, browser_type=st.browser_type, custom_path=st.browser_custom_path)



# ---------------------------------------------------------------------------
# Step 43: Approval queue, apply, run, history, stats, errors
# ---------------------------------------------------------------------------

@router.get("/queue")
async def get_approval_queue(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Semi-auto approval queue: all 'scored' listings awaiting user approval."""
    from app.services.job_tracker import get_approval_queue
    return await get_approval_queue(current_user.id, db)


@router.post("/queue/{listing_id}/approve")
async def approve_job(
    listing_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a listing — moves it to 'approved' for the next apply cycle."""
    from app.services.job_tracker import approve_listing
    result = await approve_listing(current_user.id, listing_id, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/queue/{listing_id}/reject")
async def reject_job(
    listing_id: int,
    body: ApproveRejectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a listing — marks it 'skipped'."""
    from app.services.job_tracker import reject_listing
    result = await reject_listing(current_user.id, listing_id, db, body.reason or "")
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/run")
async def run_pipeline(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger the full job application pipeline:
    Search → Score → Apply (if browser available).
    """
    from app.services.job_tracker import full_pipeline_run
    return await full_pipeline_run(current_user.id, db)


@router.get("/history")
async def get_job_history(
    application_status: Optional[str] = Query(None),
    portal: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Paginated application history."""
    query = (
        select(JobApplication, JobListing)
        .join(JobListing, JobApplication.job_listing_id == JobListing.id)
        .where(JobApplication.current_user.id == current_user.id)
    )
    if application_status:
        query = query.where(JobApplication.application_status == application_status)
    if portal:
        query = query.where(JobApplication.portal == portal)

    count_q = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_q)
    total = total_res.scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(JobApplication.applied_at.desc()).offset(offset).limit(page_size)
    res = await db.execute(query)
    rows = res.all()

    items = []
    for app, listing in rows:
        items.append({
            "id": app.id,
            "job_listing_id": app.job_listing_id,
            "job_title": listing.job_title,
            "company": listing.company,
            "portal": app.portal,
            "application_status": app.application_status,
            "error_msg": app.error_msg,
            "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            "job_url": listing.job_url,
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 1,
        "items": items,
    }


@router.get("/stats")
async def get_job_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate job application statistics."""
    from app.services.job_tracker import get_job_stats
    return await get_job_stats(current_user.id, db)


@router.get("/errors")
async def get_job_errors(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """All failed / manual_needed applications with error messages."""
    from app.services.job_tracker import get_job_errors
    return await get_job_errors(current_user.id, db)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _listing_to_dict(l: JobListing, include_description: bool = False) -> Dict[str, Any]:
    d = {
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
    if include_description:
        d["description_raw"] = l.description_raw
    return d

