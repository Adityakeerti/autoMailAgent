import base64
import smtplib
import logging
import uuid
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Contact, Setting, SendLog, ContextProfile
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

    # Determine if XOAUTH2 (Google OAuth via Gmail API HTTPS) is available
    use_xoauth2 = bool(st and st.google_refresh_token_enc)

    if not st or (not use_xoauth2 and (not st.smtp_host or not st.smtp_user)):
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

    smtp_host = st.smtp_host or "smtp.gmail.com"
    smtp_port = st.smtp_port or 587
    smtp_user = st.smtp_user or ""

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

    # --- Send ---
    if use_xoauth2:
        try:
            # Send using Gmail API (HTTPS over port 443) to bypass Render SMTP port blocks
            import httpx
            # Convert email to raw base64url format
            raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
            url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            payload = {"raw": raw_message}
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code != 200:
                    raise Exception(f"Gmail API error: {resp.text}")
            
            contact.status = "sent"
            db.add(SendLog(
                user_id=user_id,
                contact_id=contact.id,
                sent_at=datetime.datetime.utcnow(),
                status="sent",
                message_id=message_id
            ))
            await db.commit()
            logger.info(f"Email successfully sent to {contact.email} for user {user_id} via Gmail API (HTTPS)")
            return True
        except Exception as e:
            logger.error(f"Gmail API send failed for user {user_id}: {e}")
            db.add(SendLog(
                user_id=user_id,
                contact_id=contact.id,
                sent_at=datetime.datetime.utcnow(),
                status=f"failed: Gmail API error: {str(e)[:100]}",
                message_id=message_id
            ))
            await db.commit()
            return False
    else:
        # Standard SMTP sending
        try:
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
                server.ehlo()
                server.starttls()
                server.ehlo()

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
            logger.info(f"Email successfully sent to {contact.email} for user {user_id} via App Password")
            return True

        except smtplib.SMTPAuthenticationError as e:
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
            err_str = str(e)
            if "Network is unreachable" in err_str or "[Errno 101]" in err_str or "[Errno 110]" in err_str or "timed out" in err_str:
                err_detail = f"Outbound SMTP port {smtp_port} is blocked by cloud server (Render). Connect Google OAuth in Settings to send emails via HTTPS."
            else:
                err_detail = f"SMTP error: {err_str[:120]}"

            logger.error(f"Failed sending email via SMTP for user {user_id}: {e}")
            db.add(SendLog(
                user_id=user_id,
                contact_id=contact.id,
                sent_at=datetime.datetime.utcnow(),
                status=f"failed: {err_detail}",
                message_id=message_id
            ))
            await db.commit()
            return False
