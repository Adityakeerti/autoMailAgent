import base64
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


def _build_xoauth2_string(user: str, access_token: str) -> str:
    """Builds the XOAUTH2 base64 authentication string for Gmail SMTP."""
    auth_string = f"user={user}\x01auth=Bearer {access_token}\x01\x01"
    return base64.b64encode(auth_string.encode()).decode()


async def _get_valid_access_token(st: Setting) -> str | None:
    """
    Returns a fresh Google access token for the user setting.
    Refreshes via the refresh token if necessary.
    Returns None if no OAuth tokens are stored.
    """
    from app.routers.auth import get_fresh_google_access_token
    return await get_fresh_google_access_token(st)


async def send_contact_email_via_smtp(contact: Contact, db: AsyncSession) -> bool:
    user_id = contact.user_id

    res = await db.execute(select(Setting).where(Setting.user_id == user_id))
    st = res.scalar_one_or_none()

    if not st or not st.smtp_host or not st.smtp_user:
        logger.error(f"SMTP not configured for user {user_id}. Cannot send email to {contact.email}.")
        db.add(SendLog(
            user_id=user_id,
            contact_id=contact.id,
            sent_at=datetime.datetime.utcnow(),
            status="failed: SMTP not configured",
            message_id=f"<failed-{uuid.uuid4()}@automail.local>"
        ))
        await db.commit()
        return False

    smtp_host = st.smtp_host
    smtp_port = st.smtp_port or 587
    smtp_user = st.smtp_user

    # --- Determine authentication method ---
    # Priority: Google XOAUTH2 (if refresh_token present and no SMTP password is configured) > App Password > fail
    use_xoauth2 = bool(st.google_refresh_token_enc) and not bool(st.smtp_password_enc)
    access_token: str | None = None

    if use_xoauth2:
        access_token = await _get_valid_access_token(st)
        if not access_token:
            logger.error(f"Could not obtain a valid Google access token for user {user_id}. Re-authentication needed.")
            db.add(SendLog(
                user_id=user_id,
                contact_id=contact.id,
                sent_at=datetime.datetime.utcnow(),
                status="failed: Google OAuth token expired — please re-authenticate via Google",
                message_id=f"<failed-{uuid.uuid4()}@automail.local>"
            ))
            await db.commit()
            return False
        # Persist any token refresh back to DB
        await db.commit()
    else:
        # App Password / manual SMTP password
        if not st.smtp_password_enc:
            logger.error(f"No SMTP password or Google OAuth token for user {user_id}. Cannot send.")
            db.add(SendLog(
                user_id=user_id,
                contact_id=contact.id,
                sent_at=datetime.datetime.utcnow(),
                status="failed: No password configured. Set an App Password in Settings or re-connect with Google.",
                message_id=f"<failed-{uuid.uuid4()}@automail.local>"
            ))
            await db.commit()
            return False

    smtp_password = decrypt_secret(st.smtp_password_enc) if not use_xoauth2 else None

    # --- Build email message ---
    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = contact.email
    msg["Subject"] = contact.subject or "Outreach Inquiry"
    message_id = f"<{uuid.uuid4()}@{smtp_host}>"
    msg["Message-ID"] = message_id
    msg.attach(MIMEText(contact.body or "", "plain"))

    # --- Send via SMTP ---
    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.ehlo()
            server.starttls()
            server.ehlo()

        if use_xoauth2:
            xoauth2_string = _build_xoauth2_string(smtp_user, access_token)
            code, resp = server.docmd("AUTH", f"XOAUTH2 {xoauth2_string}")
            if code != 235:
                raise smtplib.SMTPAuthenticationError(code, resp)
        else:
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
        logger.info(f"Email successfully sent to {contact.email} for user {user_id} via {'XOAUTH2' if use_xoauth2 else 'App Password'}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        if use_xoauth2:
            err_detail = "XOAUTH2 authentication failed. Your Google session may have been revoked. Please re-authenticate via Google."
        else:
            err_detail = "SMTP authentication failed. Check your App Password in Settings."
        logger.error(f"SMTP auth error for user {user_id}: {e}")
        db.add(SendLog(
            user_id=user_id,
            contact_id=contact.id,
            sent_at=datetime.datetime.utcnow(),
            status=f"failed: {err_detail}",
            message_id=message_id
        ))
        await db.commit()
        return False

    except Exception as e:
        logger.error(f"Failed sending email via SMTP for user {user_id}: {e}")
        db.add(SendLog(
            user_id=user_id,
            contact_id=contact.id,
            sent_at=datetime.datetime.utcnow(),
            status=f"failed: {str(e)[:120]}",
            message_id=message_id
        ))
        await db.commit()
        return False
