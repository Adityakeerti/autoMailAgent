from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, Setting
from app.security import get_current_user, encrypt_secret, decrypt_secret

router = APIRouter(prefix="/settings", tags=["Settings"])

class SettingsUpdate(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None

    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None

    linkedin_cookie: Optional[str] = None

    send_mode: Optional[str] = None # auto, review, auto_pause_on_signal
    schedule_window: Optional[str] = None # e.g. "08:00-23:00"
    daily_target: Optional[int] = None

    job_agent_enabled: Optional[bool] = None
    browser_type: Optional[str] = None # brave, chrome, edge, custom
    browser_custom_path: Optional[str] = None
    browser_cdp_port: Optional[int] = None

class SettingsResponse(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    has_smtp_password: bool = False

    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_user: Optional[str] = None
    has_imap_password: bool = False

    has_google_oauth: bool = False  # True when user connected via Google OAuth (XOAUTH2 sending available)
    has_linkedin_cookie: bool = False

    send_mode: str
    schedule_window: str
    daily_target: int

    job_agent_enabled: bool = False
    browser_type: str = "brave"
    browser_custom_path: Optional[str] = None
    browser_cdp_port: int = 9222

@router.get("", response_model=SettingsResponse)
async def get_settings(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Setting).where(Setting.user_id == current_user.id))
    st = res.scalar_one_or_none()
    if not st:
        st = Setting(user_id=current_user.id)
        db.add(st)
        await db.commit()
        await db.refresh(st)

    return SettingsResponse(
        smtp_host=st.smtp_host,
        smtp_port=st.smtp_port,
        smtp_user=st.smtp_user,
        has_smtp_password=bool(st.smtp_password_enc),
        imap_host=st.imap_host,
        imap_port=st.imap_port,
        imap_user=st.imap_user,
        has_imap_password=bool(st.imap_password_enc),
        has_google_oauth=bool(st.google_refresh_token_enc),
        has_linkedin_cookie=bool(st.linkedin_cookie_enc),
        send_mode=st.send_mode,
        schedule_window=st.schedule_window,
        daily_target=st.daily_target,
        job_agent_enabled=bool(st.job_agent_enabled),
        browser_type=st.browser_type or "brave",
        browser_custom_path=st.browser_custom_path,
        browser_cdp_port=st.browser_cdp_port or 9222
    )

@router.put("", response_model=SettingsResponse)
async def update_settings(data: SettingsUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Setting).where(Setting.user_id == current_user.id))
    st = res.scalar_one_or_none()
    if not st:
        st = Setting(user_id=current_user.id)
        db.add(st)

    if data.smtp_host is not None: st.smtp_host = data.smtp_host
    if data.smtp_port is not None: st.smtp_port = data.smtp_port
    if data.smtp_user is not None: st.smtp_user = data.smtp_user
    if data.smtp_password is not None:
        st.smtp_password_enc = encrypt_secret(data.smtp_password)
        # Clear any existing Google OAuth tokens when configuring standard password SMTP
        st.google_refresh_token_enc = None
        st.google_access_token_enc = None
        st.google_token_expiry = None

    if data.imap_host is not None: st.imap_host = data.imap_host
    if data.imap_port is not None: st.imap_port = data.imap_port
    if data.imap_user is not None: st.imap_user = data.imap_user
    if data.imap_password is not None: st.imap_password_enc = encrypt_secret(data.imap_password)

    if data.linkedin_cookie is not None: st.linkedin_cookie_enc = encrypt_secret(data.linkedin_cookie)

    if data.send_mode is not None:
        if data.send_mode not in ["auto", "review", "auto_pause_on_signal"]:
            raise HTTPException(status_code=400, detail="Invalid send_mode. Must be auto, review, or auto_pause_on_signal")
        st.send_mode = data.send_mode
    if data.schedule_window is not None: st.schedule_window = data.schedule_window
    if data.daily_target is not None: st.daily_target = data.daily_target

    if data.job_agent_enabled is not None: st.job_agent_enabled = data.job_agent_enabled
    if data.browser_type is not None:
        valid_browsers = ["brave", "chrome", "edge", "custom"]
        if data.browser_type.lower() not in valid_browsers:
            raise HTTPException(status_code=400, detail=f"Invalid browser_type. Must be one of: {', '.join(valid_browsers)}")
        st.browser_type = data.browser_type.lower()
    if data.browser_custom_path is not None: st.browser_custom_path = data.browser_custom_path
    if data.browser_cdp_port is not None:
        if data.browser_cdp_port < 1024 or data.browser_cdp_port > 65535:
            raise HTTPException(status_code=400, detail="Invalid CDP port. Must be between 1024 and 65535.")
        st.browser_cdp_port = data.browser_cdp_port

    await db.commit()
    await db.refresh(st)

    return SettingsResponse(
        smtp_host=st.smtp_host,
        smtp_port=st.smtp_port,
        smtp_user=st.smtp_user,
        has_smtp_password=bool(st.smtp_password_enc),
        imap_host=st.imap_host,
        imap_port=st.imap_port,
        imap_user=st.imap_user,
        has_imap_password=bool(st.imap_password_enc),
        has_google_oauth=bool(st.google_refresh_token_enc),
        has_linkedin_cookie=bool(st.linkedin_cookie_enc),
        send_mode=st.send_mode,
        schedule_window=st.schedule_window,
        daily_target=st.daily_target,
        job_agent_enabled=bool(st.job_agent_enabled),
        browser_type=st.browser_type or "brave",
        browser_custom_path=st.browser_custom_path,
        browser_cdp_port=st.browser_cdp_port or 9222
    )

@router.post("/clear-pipeline")
async def clear_pipeline(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Clears all pipeline data (contacts, scraper queue, logs, job listings/applications) except personal info, settings, and templates"""
    from sqlalchemy import delete
    from app.models import Contact, ScrapeQueue, SendLog, JobListing, JobApplication

    user_id = current_user.id

    # 1. Delete contacts
    await db.execute(delete(Contact).where(Contact.user_id == user_id))
    # 2. Delete scrape queue items
    await db.execute(delete(ScrapeQueue).where(ScrapeQueue.user_id == user_id))
    # 3. Delete send logs
    await db.execute(delete(SendLog).where(SendLog.user_id == user_id))
    # 4. Delete job applications
    await db.execute(delete(JobApplication).where(JobApplication.user_id == user_id))
    # 5. Delete job listings
    await db.execute(delete(JobListing).where(JobListing.user_id == user_id))

    await db.commit()

    return {"message": "Pipeline cleared successfully! Your profile context, SMTP settings, templates, and resumes have been preserved."}
