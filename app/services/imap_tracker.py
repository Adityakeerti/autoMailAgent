import imaplib
import email
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Setting, Contact, SendLog
from app.security import decrypt_secret

logger = logging.getLogger("imap_tracker")

async def check_user_inbox_for_replies_and_bounces(user_id: int, db: AsyncSession):
    res = await db.execute(select(Setting).where(Setting.user_id == user_id))
    st = res.scalar_one_or_none()

    if not st or not st.imap_host or not st.imap_user or not st.imap_password_enc:
        return

    imap_password = decrypt_secret(st.imap_password_enc)
    try:
        mail = imaplib.IMAP4_SSL(st.imap_host, st.imap_port or 993)
        mail.login(st.imap_user, imap_password)
        mail.select("inbox")

        # Search unread messages
        status, response = mail.search(None, "UNSEEN")
        if status != "OK":
            return

        msg_ids = response[0].split()
        signal_detected = False

        for num in msg_ids[-10:]: # Check last 10 unseen
            res_fetch, data = mail.fetch(num, "(RFC822)")
            if res_fetch != "OK":
                continue

            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            from_header = msg.get("From", "")
            subject_header = msg.get("Subject", "")
            in_reply_to = msg.get("In-Reply-To", "")
            body = ""

            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            is_bounce = "mailer-daemon" in from_header.lower() or "undeliverable" in subject_header.lower() or "bounce" in body.lower()

            # Find matching contact by In-Reply-To or From email
            res_c = await db.execute(select(Contact).where(Contact.user_id == user_id))
            contacts = res_c.scalars().all()

            for c in contacts:
                if c.email in from_header or (in_reply_to and in_reply_to in (c.subject or "")):
                    if is_bounce:
                        c.status = "bounced"
                    else:
                        c.status = "replied"
                    signal_detected = True

        if signal_detected and st.send_mode == "auto_pause_on_signal":
            logger.info(f"Signal (reply/bounce) detected for user {user_id}. Pausing queue.")
            st.send_mode = "review"

        await db.commit()
        mail.close()
        mail.logout()

    except Exception as e:
        logger.warning(f"IMAP check failed for user {user_id}: {e}")
