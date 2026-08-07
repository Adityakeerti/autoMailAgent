import asyncio
import datetime
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, func

from app.database import AsyncSessionLocal
from app.models import User, Setting, Contact, SendLog
from app.services.smtp_sender import send_contact_email_via_smtp
from app.services.imap_tracker import check_user_inbox_for_replies_and_bounces

logger = logging.getLogger("queue_scheduler")
scheduler = AsyncIOScheduler()

def is_within_schedule_window(window_str: str) -> bool:
    try:
        start_str, end_str = window_str.split("-")
        sh, sm = map(int, start_str.split(":"))
        eh, em = map(int, end_str.split(":"))

        # Evaluate time in India Standard Time (IST: UTC+5:30)
        ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        now = datetime.datetime.now(ist_tz).time()
        start_time = datetime.time(sh, sm)
        end_time = datetime.time(eh, em)

        return start_time <= now <= end_time
    except Exception:
        return True # Default open if invalid window string

async def process_user_queue(user_id: int):
    async with AsyncSessionLocal() as db:
        res_st = await db.execute(select(Setting).where(Setting.user_id == user_id))
        st = res_st.scalar_one_or_none()
        if not st:
            return

        # Check schedule window
        if not is_within_schedule_window(st.schedule_window or "08:00-23:00"):
            logger.info(f"User {user_id} outside schedule window.")
            return

        # Check send mode
        if st.send_mode == "review":
            logger.info(f"User {user_id} is in 'review' mode. Queued contacts will not send automatically.")
            return

        # If send_mode is auto, automatically personalize new/generic_new contacts
        if st.send_mode == "auto":
            res_new = await db.execute(
                select(Contact).where(
                    Contact.user_id == user_id,
                    Contact.status.in_(["new", "generic_new"])
                ).order_by(Contact.id.asc()).limit(5)
            )
            new_contacts = res_new.scalars().all()
            for nc in new_contacts:
                try:
                    from app.services.renderer import render_contact_email
                    logger.info(f"Auto-personalizing contact {nc.id} for user {user_id}")
                    await render_contact_email(nc.id, None, db)
                except Exception as e:
                    logger.error(f"Auto-personalization failed for contact {nc.id}: {e}")

        # Rate limiter check: count sends in current hour
        one_hour_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        res_count = await db.execute(
            select(func.count(SendLog.id)).where(SendLog.user_id == user_id, SendLog.sent_at >= one_hour_ago)
        )
        sends_this_hour = res_count.scalar() or 0

        # Rate limit: max 3 sends/hour per user
        if sends_this_hour >= 3:
            logger.info(f"User {user_id} reached rate limit of {sends_this_hour} sends in last hour.")
            return

        # Fetch next contact to send
        res_c = await db.execute(
            select(Contact).where(
                Contact.user_id == user_id,
                Contact.status.in_(["queued", "personalized", "generic_queued"])
            ).order_by(Contact.id.asc()).limit(1)
        )
        contact = res_c.scalar_one_or_none()

        if contact:
            logger.info(f"Scheduler processing send for user {user_id}, contact {contact.id}")
            await send_contact_email_via_smtp(contact, db)

async def global_scheduler_tick():
    async with AsyncSessionLocal() as db:
        res_users = await db.execute(select(User.id))
        user_ids = res_users.scalars().all()

    for uid in user_ids:
        try:
            await process_user_queue(uid)
            async with AsyncSessionLocal() as db:
                await check_user_inbox_for_replies_and_bounces(uid, db)
        except Exception as e:
            logger.error(f"Error processing queue for user {uid}: {e}")

async def global_batch_scraping():
    logger.info("Starting scheduled global batch scraping...")
    from app.services.scrapers import run_batch_scraping
    async with AsyncSessionLocal() as db:
        res_users = await db.execute(select(User.id))
        user_ids = res_users.scalars().all()
        
    for uid in user_ids:
        try:
            async with AsyncSessionLocal() as db:
                count = await run_batch_scraping(uid, db)
                if count > 0:
                    logger.info(f"Scheduled batch scraping for user {uid} added {count} contacts.")
        except Exception as e:
            logger.error(f"Error in scheduled batch scraping for user {uid}: {e}")

def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(global_scheduler_tick, 'interval', minutes=1, id='automail_queue_job')
        scheduler.add_job(global_batch_scraping, 'interval', hours=6, id='automail_batch_scrape')
        scheduler.start()

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
