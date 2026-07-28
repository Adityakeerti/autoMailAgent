from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, Setting, ScrapeQueue
from app.security import get_current_user
from app.services.scrapers import scraper_service, normalize_scrape_queue

router = APIRouter(prefix="/scrapers", tags=["Scrapers"])

class ScrapeUrlRequest(BaseModel):
    url: str

class ScrapeGithubRequest(BaseModel):
    username_or_repo: str

class QueueItemResponse(BaseModel):
    id: int
    user_id: int
    source: str
    raw_data: dict
    discovered_at: str
    status: str

class EnrichApolloRequest(BaseModel):
    first_name: str
    last_name: str
    company_domain: str

@router.post("/career-page", response_model=QueueItemResponse)
async def scrape_career_page(req: ScrapeUrlRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await scraper_service.scrape_career_page(req.url)
    item = ScrapeQueue(
        user_id=current_user.id,
        source="career_page",
        raw_data=result,
        status="pending"
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return QueueItemResponse(
        id=item.id,
        user_id=item.user_id,
        source=item.source,
        raw_data=item.raw_data,
        discovered_at=item.discovered_at.isoformat() + "Z",
        status=item.status
    )

@router.post("/github", response_model=QueueItemResponse)
async def scrape_github(req: ScrapeGithubRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await scraper_service.scrape_github(req.username_or_repo)
    item = ScrapeQueue(
        user_id=current_user.id,
        source="github",
        raw_data=result,
        status="pending"
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return QueueItemResponse(
        id=item.id,
        user_id=item.user_id,
        source=item.source,
        raw_data=item.raw_data,
        discovered_at=item.discovered_at.isoformat() + "Z",
        status=item.status
    )

@router.post("/job-portal", response_model=QueueItemResponse)
async def scrape_job_portal(req: ScrapeUrlRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await scraper_service.scrape_job_portal(req.url)
    item = ScrapeQueue(
        user_id=current_user.id,
        source="job_portal",
        raw_data=result,
        status="pending"
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return QueueItemResponse(
        id=item.id,
        user_id=item.user_id,
        source=item.source,
        raw_data=item.raw_data,
        discovered_at=item.discovered_at.isoformat() + "Z",
        status=item.status
    )

@router.post("/linkedin", response_model=QueueItemResponse)
async def scrape_linkedin(req: ScrapeUrlRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Setting).where(Setting.user_id == current_user.id))
    st = res.scalar_one_or_none()
    linkedin_cookie = st.linkedin_cookie_enc if st else None

    result = await scraper_service.scrape_linkedin(linkedin_cookie, req.url)
    item = ScrapeQueue(
        user_id=current_user.id,
        source="linkedin",
        raw_data=result,
        status="pending"
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return QueueItemResponse(
        id=item.id,
        user_id=item.user_id,
        source=item.source,
        raw_data=item.raw_data,
        discovered_at=item.discovered_at.isoformat() + "Z",
        status=item.status
    )

@router.post("/auto-discover")
async def auto_discover_jobs(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Auto-searches job platforms using user's saved job preferences"""
    result = await scraper_service.auto_discover_jobs(current_user.id, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # If no NEW leads were found, skip saving to DB and return a clear message
    if result.get("total_unique_emails", 0) == 0:
        return {
            "id": -1,
            "user_id": current_user.id,
            "source": "auto_discover",
            "raw_data": result,
            "discovered_at": "",
            "status": "no_new_leads",
            "message": "No new leads found. All discovered emails already exist in your contacts or were already queued."
        }

    item = ScrapeQueue(
        user_id=current_user.id,
        source="auto_discover",
        raw_data=result,
        status="pending"
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    # Auto-normalize immediately so discovered contacts enter the contacts store & send queue
    new_count = await normalize_scrape_queue(current_user.id, db)
    return {
        "id": item.id,
        "user_id": item.user_id,
        "source": item.source,
        "raw_data": item.raw_data,
        "discovered_at": item.discovered_at.isoformat() + "Z",
        "status": item.status,
        "new_contacts_added": new_count
    }


@router.post("/enrich/apollo", response_model=QueueItemResponse)
async def enrich_with_apollo(req: EnrichApolloRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Finds verified email using Apollo.io people match"""
    result = await scraper_service.enrich_email_apollo(req.first_name, req.last_name, req.company_domain)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    item = ScrapeQueue(
        user_id=current_user.id,
        source="apollo",
        raw_data=result,
        status="pending"
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return QueueItemResponse(
        id=item.id, user_id=item.user_id, source=item.source,
        raw_data=item.raw_data, discovered_at=item.discovered_at.isoformat() + "Z", status=item.status
    )

@router.post("/batch")
async def trigger_batch_scraping(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Triggers bulk scraping of target companies' career pages & GitHub orgs"""
    from app.services.scrapers import run_batch_scraping
    count = await run_batch_scraping(current_user.id, db)
    return {"message": f"Batch scraping finished. Normalized {count} new contacts."}

@router.post("/normalize")
async def run_normalizer(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    count = await normalize_scrape_queue(current_user.id, db)
    return {"message": f"Normalized {count} new contacts into contacts store"}

@router.get("/queue", response_model=List[QueueItemResponse])
async def list_scrape_queue(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ScrapeQueue).where(ScrapeQueue.user_id == current_user.id))
    items = res.scalars().all()
    return [
        QueueItemResponse(
            id=item.id,
            user_id=item.user_id,
            source=item.source,
            raw_data=item.raw_data,
            discovered_at=item.discovered_at.isoformat() + "Z",
            status=item.status
        )
        for item in items
    ]
