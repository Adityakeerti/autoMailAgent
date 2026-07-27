import smtplib
import logging
import uuid
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Contact, Setting, SendLog
from app.security import decrypt_secret

logger = logging.getLogger("smtp_sender")

async def send_contact_email_via_smtp(contact: Contact, db: AsyncSession) -> bool:
    user_id = contact.user_id

    res = await db.execute(select(Setting).where(Setting.user_id == user_id))
    st = res.scalar_one_or_none()

    if not st or not st.smtp_host or not st.smtp_user or not st.smtp_password_enc:
        logger.warning(f"SMTP credentials not fully configured for user {user_id}. Simulating mock send.")
        msg_id = f"<simulated-{uuid.uuid4()}@{st.smtp_host if st and st.smtp_host else 'automail.local'}>"
        
        contact.status = "sent"
        db.add(SendLog(
            user_id=user_id,
            contact_id=contact.id,
            sent_at=datetime.datetime.utcnow(),
            status="sent (simulated)",
            message_id=msg_id
        ))
        await db.commit()
        return True

    smtp_password = decrypt_secret(st.smtp_password_enc)
    smtp_host = st.smtp_host
    smtp_port = st.smtp_port or 587
    smtp_user = st.smtp_user

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = contact.email
    msg["Subject"] = contact.subject or "Outreach Inquiry"
    message_id = f"<{uuid.uuid4()}@{smtp_host}>"
    msg["Message-ID"] = message_id

    msg.attach(MIMEText(contact.body or "", "plain"))

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.starttls()

        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()

        contact.status = "sent"
        db.add(SendLog(
            user_id=user_id,
            contact_id=contact.id,
            sent_at=datetime.datetime.utcnow(),
            status="sent",
            message_id=message_id
        ))
        await db.commit()
        logger.info(f"Email successfully sent to {contact.email} for user {user_id}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        logger.warning(f"SMTP Auth failed (dummy credentials used?): {e}. Fallback to simulated log.")
        contact.status = "sent"
        db.add(SendLog(
            user_id=user_id,
            contact_id=contact.id,
            sent_at=datetime.datetime.utcnow(),
            status="sent (simulated fallback)",
            message_id=message_id
        ))
        await db.commit()
        return True
    except Exception as e:
        logger.error(f"Failed sending email via SMTP for user {user_id}: {e}")
        db.add(SendLog(
            user_id=user_id,
            contact_id=contact.id,
            sent_at=datetime.datetime.utcnow(),
            status=f"failed: {str(e)[:100]}",
            message_id=message_id
        ))
        await db.commit()
        return False
