import re
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import ScrapeQueue, Contact
from app.security import decrypt_secret

logger = logging.getLogger("scrapers")

EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

def extract_public_emails(text: str) -> List[str]:
    matches = re.findall(EMAIL_REGEX, text)
    # Filter out fake images / placeholder extensions (.png, .jpg, .svg, etc)
    valid = []
    for m in set(matches):
        m_lower = m.lower()
        if not any(m_lower.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp", "example.com", "domain.com"]):
            valid.append(m)
    return valid

class ScraperService:

    async def scrape_career_page(self, url: str) -> Dict[str, Any]:
        """Scrape static HTML career page for contact emails and role details"""
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            title = soup.title.string.strip() if soup.title and soup.title.string else "Career Page"
            emails = extract_public_emails(html)

            return {
                "source": "career_page",
                "url": url,
                "title": title,
                "found_emails": emails,
                "raw_text": soup.get_text()[:2000]
            }

    async def scrape_github(self, username_or_repo: str) -> Dict[str, Any]:
        """Scrape public GitHub user bio or README for email"""
        url = f"https://api.github.com/users/{username_or_repo}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers={"User-Agent": "AutoMail-Bot"})
            if resp.status_code == 200:
                data = resp.json()
                email = data.get("email")
                bio = data.get("bio", "") or ""
                emails = [email] if email else extract_public_emails(bio)
                return {
                    "source": "github",
                    "url": data.get("html_url", url),
                    "name": data.get("name") or username_or_repo,
                    "company": data.get("company"),
                    "found_emails": [e for e in emails if e],
                    "raw_data": data
                }
            else:
                # Fallback to web scrape
                web_url = f"https://github.com/{username_or_repo}"
                w_resp = await client.get(web_url, headers={"User-Agent": "Mozilla/5.0"})
                emails = extract_public_emails(w_resp.text)
                return {
                    "source": "github",
                    "url": web_url,
                    "name": username_or_repo,
                    "found_emails": emails
                }

    async def scrape_job_portal(self, url: str) -> Dict[str, Any]:
        """Scrape job portal listing (Naukri/Indeed/LinkedIn Jobs) for listed recruiter email"""
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")
            emails = extract_public_emails(html)
            
            return {
                "source": "job_portal",
                "url": url,
                "found_emails": emails,
                "raw_text": soup.get_text()[:2000]
            }

    async def scrape_linkedin(self, linkedin_cookie_enc: Optional[str], profile_or_job_url: str) -> Dict[str, Any]:
        """LinkedIn scraper using system shared account cookie or user custom cookie (rate limited)"""
        cookie = decrypt_secret(linkedin_cookie_enc) if linkedin_cookie_enc else None
        if not cookie and settings.SHARED_LINKEDIN_COOKIE:
            cookie = settings.SHARED_LINKEDIN_COOKIE

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        if cookie:
            headers["Cookie"] = f"li_at={cookie}"

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(profile_or_job_url, headers=headers)
            html = resp.text
            emails = extract_public_emails(html)
            return {
                "source": "linkedin",
                "url": profile_or_job_url,
                "found_emails": emails,
                "using_system_account": not bool(linkedin_cookie_enc),
                "raw_text": html[:1000]
            }

scraper_service = ScraperService()

async def normalize_scrape_queue(user_id: int, db: AsyncSession) -> int:
    """Normalizes items in scrape_queue -> contacts table, strictly enforcing public email discovery"""
    res = await db.execute(
        select(ScrapeQueue).where(ScrapeQueue.user_id == user_id, ScrapeQueue.status == "pending")
    )
    items = res.scalars().all()
    count = 0

    for item in items:
        raw = item.raw_data or {}
        emails = raw.get("found_emails", [])
        source = item.source
        url = raw.get("url")

        for email in emails:
            # Check if contact already exists for user
            existing = await db.execute(
                select(Contact).where(Contact.user_id == user_id, Contact.email == email)
            )
            if not existing.scalar_one_or_none():
                db.add(Contact(
                    user_id=user_id,
                    name=raw.get("name") or raw.get("company") or "Hiring Manager",
                    company=raw.get("company") or "Target Company",
                    role=raw.get("role") or "Recruiter / Engineering Lead",
                    source=source,
                    job_posting_url=url,
                    email=email,
                    status="new"
                ))
                count += 1

        item.status = "processed"

    await db.commit()
    return count
