from fastapi import APIRouter

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "AutoMail Multi-User Backend"}

@router.get("/ping")
async def ping_check():
    return {"status": "ok", "service": "AutoMail Multi-User Backend"}

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Setting, User
from app.security import get_current_user
from sqlalchemy import select

@router.get("/debug-settings")
async def debug_settings(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Setting).where(Setting.user_id == current_user.id))
    st = res.scalar_one_or_none()
    if not st:
        return {"error": "No setting found"}
    return {
        "user_id": current_user.id,
        "google_refresh_token_enc_is_null": st.google_refresh_token_enc is None,
        "google_refresh_token_enc_val": str(st.google_refresh_token_enc)[:15] if st.google_refresh_token_enc else None,
        "smtp_password_enc_is_null": st.smtp_password_enc is None,
        "smtp_password_enc_val": str(st.smtp_password_enc)[:15] if st.smtp_password_enc else None,
        "smtp_host": st.smtp_host,
        "smtp_port": st.smtp_port,
        "smtp_user": st.smtp_user,
    }

from app.models import SendLog

@router.get("/debug-logs")
async def debug_logs(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(SendLog).where(SendLog.user_id == current_user.id).order_by(SendLog.sent_at.desc()).limit(10)
    )
    logs = res.scalars().all()
    return [
        {
            "id": l.id,
            "contact_id": l.contact_id,
            "sent_at": l.sent_at.isoformat() if l.sent_at else None,
            "status": l.status,
            "message_id": l.message_id
        }
        for l in logs
    ]

from app.models import Contact, ScrapeQueue, JobListing, JobApplication
from sqlalchemy import delete

@router.post("/clean-data")
async def clean_user_data(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.execute(delete(SendLog).where(SendLog.user_id == current_user.id))
    await db.execute(delete(Contact).where(Contact.user_id == current_user.id))
    await db.execute(delete(ScrapeQueue).where(ScrapeQueue.user_id == current_user.id))
    await db.execute(delete(JobApplication).where(JobApplication.user_id == current_user.id))
    await db.execute(delete(JobListing).where(JobListing.user_id == current_user.id))
    await db.commit()
    return {"status": "ok", "message": "Scraped jobs, applications, logs, and contacts have been cleaned for your user."}




