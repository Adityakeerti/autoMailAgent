import re
import random
import logging
import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import ScrapeQueue, Contact, JobPreference
from app.security import decrypt_secret
from app.config import settings

logger = logging.getLogger("scrapers")

EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
]

# Domains to exclude from synthesized recruitment emails
JOB_BOARD_DOMAINS = {
    "linkedin.com", "indeed.com", "glassdoor.com", "naukri.com",
    "remotive.com", "jobicy.com", "lever.co", "greenhouse.io",
    "workday.com", "bamboohr.com", "ashbyhq.com", "smartrecruiters.com",
    "icims.com", "taleo.net", "successfactors.com", "recruitee.com",
    "ziprecruiter.com", "monster.com", "dice.com", "wellfound.com",
    "angellist.com", "simplyhired.com", "careerbuilder.com"
}

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "protonmail.com", "icloud.com", "live.com", "ymail.com",
    "aol.com", "msn.com", "rediffmail.com"
}


def _random_ua() -> str:
    return random.choice(USER_AGENTS)


def _company_from_url(url: str) -> Optional[str]:
    """Extract a best-guess company name from a URL domain."""
    if not url:
        return None
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        host = parsed.hostname or ""

        # Known ATS/job-board domains that embed company name in path (e.g. lever.co/stripe)
        ATS_IN_PATH = {"lever.co", "greenhouse.io", "ashbyhq.com", "workable.com", "recruitee.com",
                       "smartrecruiters.com", "breezy.hr", "jobs.lever.co", "boards.greenhouse.io"}
        for ats in ATS_IN_PATH:
            if host == ats or host.endswith("." + ats):
                # First path segment is the company slug (e.g. /stripe/...)
                parts = [p for p in parsed.path.split("/") if p]
                if parts:
                    return parts[0].replace("-", " ").title()

        # Generic job/career subdomain names to skip — look at second-level domain instead
        SKIP_SUBDOMAINS = {"jobs", "careers", "career", "hiring", "recruit", "work", "apply", "join", "talent"}
        host_stripped = re.sub(r'^www\.', '', host)
        parts = host_stripped.split(".")
        if len(parts) >= 2:
            subdomain = parts[0].lower()
            if subdomain in SKIP_SUBDOMAINS:
                # Use the second-level domain instead (e.g. careers.shopify.com → "Shopify")
                name = parts[1]
            else:
                name = parts[0]
        else:
            name = parts[0] if parts else ""

        if name and len(name) >= 2 and not name.isnumeric():
            return name.title()
    except Exception:
        pass
    return None


def _extract_company_from_page(soup, url: str) -> Optional[str]:
    """
    Try to extract a real company name from page HTML in order of confidence:
    1. og:site_name meta tag (most reliable)
    2. application-name meta tag
    3. Page <title> cleaned up (strip common suffixes like 'Jobs', 'Careers', etc.)
    4. URL domain as last resort
    Returns None only if nothing reasonable found.
    """
    # 1. og:site_name
    og = soup.find("meta", property="og:site_name")
    if og and og.get("content", "").strip():
        return og["content"].strip()

    # 2. application-name
    app_name = soup.find("meta", attrs={"name": "application-name"})
    if app_name and app_name.get("content", "").strip():
        return app_name["content"].strip()

    # 3. Clean page title (strip trailing " – Careers", " Jobs", etc.)
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
        # Remove common trailing suffixes
        title = re.sub(
            r'[\s\-–|]+(?:jobs?|careers?|hiring|opportunities|work with us|join us|open positions?)[\s\-–|]*$',
            '', title, flags=re.IGNORECASE
        ).strip()
        # If title still looks like a domain or is very short, skip
        if title and len(title) >= 3 and '.' not in title:
            return title

    # 4. URL domain fallback
    return _company_from_url(url)


def _sanitize_domain(company_name: str) -> Optional[str]:
    if not company_name:
        return None
    cleaned = re.sub(r'[^\w\s]', '', company_name)
    cleaned = re.sub(
        r'\b(inc|llc|ltd|corp|corporation|gmbh|co|private|limited|services|group|technologies|tech|solutions)\b',
        '', cleaned, flags=re.IGNORECASE
    )
    cleaned = re.sub(r'\s+', '', cleaned).lower().strip()
    if len(cleaned) >= 3 and not cleaned.isnumeric():
        return f"{cleaned}.com"
    return None


def _is_quality_email(email: str) -> bool:
    """
    Returns True if email looks like a real company recruitment contact.
    Rejects: free consumer domains, known job-board/ATS domains,
    very long domains, and malformed addresses.
    """
    try:
        _, domain = email.lower().split("@", 1)
    except ValueError:
        return False
    if domain in FREE_EMAIL_DOMAINS:
        return False
    if domain in JOB_BOARD_DOMAINS:
        return False
    # Reject sub-domains of known job boards (e.g. jobs.linkedin.com)
    for jb in JOB_BOARD_DOMAINS:
        if domain.endswith("." + jb):
            return False
    if len(domain) > 40:
        return False
    # Must have a valid TLD
    parts = domain.split(".")
    if len(parts) < 2 or not (2 <= len(parts[-1]) <= 6):
        return False
    return True


def _match_job(job_title: str, category: str, search_tokens: List[str]) -> bool:
    """
    Checks if a job title or category matches the search tokens.
    Uses word-subset matching: all words of at least one search token must be present 
    as sub-words of the job title/category words (exact match enforced for short words).
    """
    if not job_title:
        return False
    
    title_clean = re.sub(r'[^\w\s]', ' ', job_title.lower())
    title_words = set(title_clean.split())
    
    category_clean = re.sub(r'[^\w\s]', ' ', category.lower()) if category else ""
    category_words = set(category_clean.split())
    
    for token in search_tokens:
        token_clean = re.sub(r'[^\w\s]', ' ', token.lower())
        token_words = token_clean.split()
        if not token_words:
            continue
        
        match = True
        for tw in token_words:
            # Enforce exact match for short words like 'ai', 'ml', 'sde', 'swe' (len <= 3)
            if len(tw) <= 3:
                if tw not in title_words and tw not in category_words:
                    match = False
                    break
            else:
                if not any(tw in w for w in title_words) and not any(tw in w for w in category_words):
                    match = False
                    break
        if match:
            return True
            
    return False



def _extract_name_from_comment(text: str, email: str) -> str:
    # Try from email first part
    username = email.split("@")[0].lower()
    generic_words = {"jobs", "careers", "hiring", "recruiting", "hr", "apply", "contact", "info", "hello", "team", "talent", "recruiter", "work", "join", "admin", "support", "developer", "engineering"}
    
    if username not in generic_words:
        # If it contains dots/underscores
        parts = re.split(r'[._-]', username)
        if len(parts) >= 2 and all(p.isalpha() for p in parts[:2]):
            return f"{parts[0].capitalize()} {parts[1].capitalize()}"
        elif len(parts) == 1 and parts[0].isalpha() and len(parts[0]) > 2:
            return parts[0].capitalize()
    
    # Try to find a name in the comment text.
    # Look for common signatures like: "Name - Founder" or "— Name" or "- Name"
    # Clean HTML tags if any
    clean_text = re.sub(r'<[^>]*>', ' ', text)
    # Search for lines starting with - or — followed by 2-3 words
    sig_match = re.search(r'(?:^|\n)[—\-]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})', clean_text)
    if sig_match:
        return sig_match.group(1).strip()
        
    # Search for "reach out to [Name]" or "email [Name] at"
    match = re.search(r'\b(?:reach out to|contact|email)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', clean_text)
    if match:
        candidate = match.group(1).strip()
        if candidate.lower() not in {"us", "me", "our", "the", "him", "her", "them"}:
            return candidate
            
    return "Hiring Manager"


def extract_public_emails(text: str) -> List[str]:
    matches = re.findall(EMAIL_REGEX, text)
    skip_ext = [".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp"]
    skip_domains = ["example.com", "domain.com", "sentry.io", "wixpress.com"]
    valid = []
    for m in set(matches):
        m_lower = m.lower()
        if any(m_lower.endswith(ext) for ext in skip_ext):
            continue
        if any(d in m_lower for d in skip_domains):
            continue
        valid.append(m)
    return valid


async def _safe_get(
    client: httpx.AsyncClient,
    url: str,
    headers: Optional[Dict[str, str]] = None
) -> Optional[httpx.Response]:
    """Safe HTTP GET wrapper — gracefully handles DNS / network errors."""
    try:
        h = {"User-Agent": _random_ua()}
        if headers:
            h.update(headers)
        resp = await client.get(url, headers=h, follow_redirects=True)
        if resp.status_code == 200:
            return resp
    except Exception as e:
        logger.debug(f"Safe fetch skipped for {url}: {e}")
    return None


class ScraperService:

    async def scrape_career_page(self, url: str) -> Dict[str, Any]:
        """Scrape static HTML career page for contact emails and role details (Deactivated)"""
        return {"source": "career_page", "url": url, "title": "Career Page", "found_emails": [], "found_leads": []}

    async def scrape_github(self, username_or_repo: str) -> Dict[str, Any]:
        """Scrape public GitHub user bio or README for email (Deactivated)"""
        return {
            "source": "github",
            "url": f"https://github.com/{username_or_repo}",
            "name": username_or_repo,
            "found_emails": [],
            "found_leads": []
        }

    async def scrape_job_portal(self, url: str) -> Dict[str, Any]:
        """Scrape job portal listing for emails (Deactivated)"""
        return {"source": "job_portal", "url": url, "found_emails": [], "found_leads": []}

    async def scrape_linkedin(self, linkedin_cookie_enc: Optional[str], profile_or_job_url: str) -> Dict[str, Any]:
        """LinkedIn scraper using session cookie"""
        cookie = decrypt_secret(linkedin_cookie_enc) if linkedin_cookie_enc else None
        if not cookie and settings.SHARED_LINKEDIN_COOKIE:
            cookie = settings.SHARED_LINKEDIN_COOKIE

        headers = {"User-Agent": _random_ua()}
        if cookie:
            headers["Cookie"] = f"li_at={cookie}"

        status_reason = "success"
        html = ""
        status_code = None

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                resp = await client.get(profile_or_job_url, headers=headers)
                status_code = resp.status_code
                html = resp.text
                
                is_auth_wall = (
                    "login" in str(resp.url) or 
                    "signup" in str(resp.url) or 
                    "authwall" in str(resp.url) or 
                    "Sign in to LinkedIn" in html or 
                    "Join LinkedIn" in html
                )
                
                if is_auth_wall:
                    status_reason = "auth_failed"
                elif status_code in (429, 999) or "Too Many Requests" in html or "quick checkpoint" in html or "Security Checkpoint" in html:
                    status_reason = "blocked_or_throttled"
                elif status_code != 200:
                    status_reason = f"failed_status_{status_code}"
            except Exception as e:
                logger.debug(f"LinkedIn fetch skipped for {profile_or_job_url}: {e}")
                status_reason = "network_error"

        if status_reason != "success" or not html:
            return {
                "source": "linkedin",
                "url": profile_or_job_url,
                "found_emails": [],
                "found_leads": [],
                "status": "failed",
                "reason": status_reason,
                "status_code": status_code
            }

        emails = [e for e in extract_public_emails(html) if _is_quality_email(e)]
        leads = [{"email": e, "company": "LinkedIn Contact", "job_title": "Recruiter", "job_url": profile_or_job_url, "platform": "linkedin"} for e in emails]
        
        final_reason = "success"
        if not emails:
            final_reason = "no_leads_found"

        return {
            "source": "linkedin",
            "url": profile_or_job_url,
            "found_emails": emails,
            "found_leads": leads,
            "using_system_account": not bool(linkedin_cookie_enc),
            "status": "success" if emails else "failed",
            "reason": final_reason,
            "status_code": status_code,
            "raw_text": html[:1000]
        }

    async def auto_discover_jobs(self, user_id: int, db: AsyncSession) -> Dict[str, Any]:
        """
        Multi-Source Auto-Discover Job Scraper (Deactivated).
        """
        return {
            "source": "auto_discover",
            "roles_searched": [],
            "expanded_keywords_by_role": {},
            "location": "",
            "platforms_searched": [],
            "found_emails": [],
            "found_leads": [],
            "results_by_platform": [],
            "total_unique_emails": 0
        }

    async def enrich_email_apollo(self, first_name: str, last_name: str, company_domain: str) -> Dict[str, Any]:
        """Uses Apollo.io people/match API to find a verified email (Deactivated)."""
        return {
            "source": "apollo",
            "found_emails": [],
            "found_leads": [],
            "name": f"{first_name} {last_name}".strip(),
            "title": "Contact",
            "company": company_domain
        }

    async def find_and_enrich_tech_lead(self, company_domain: str) -> Optional[Dict[str, Any]]:
        """Searches Apollo for a tech leader/engineering manager (Deactivated)."""
        return None

    async def scrape_hn_hiring(self, search_tokens: List[str], max_comments: int = 50) -> Dict[str, Any]:
        """Scrapes the latest HN 'Who is Hiring' thread (Deactivated)."""
        return {"source": "hn_hiring", "found_emails": [], "found_leads": []}

    async def scrape_arbeitnow(self, search_tokens: List[str]) -> Dict[str, Any]:
        """Scrape Arbeitnow API for matching job postings (Deactivated)."""
        return {"source": "arbeitnow", "found_emails": [], "found_leads": []}

    async def scrape_ats_direct(self, search_tokens: List[str], companies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Scrapes Lever and Greenhouse directly for job postings (Deactivated)."""
        return {"source": "ats_direct", "matched_jobs": []}


scraper_service = ScraperService()


async def normalize_scrape_queue(user_id: int, db: AsyncSession) -> int:
    """
    Normalizes items in scrape_queue -> contacts table.
    Uses rich per-email `found_leads` metadata when available (includes job_posting_url).
    Falls back to flat `found_emails` list for legacy entries.
    """
    res = await db.execute(
        select(ScrapeQueue).where(ScrapeQueue.user_id == user_id, ScrapeQueue.status == "pending")
    )
    items = res.scalars().all()
    count = 0

    for item in items:
        raw = item.raw_data or {}
        source = item.source

        # Prefer rich per-email lead metadata (new format)
        leads = raw.get("found_leads", [])
        if not leads:
            # Fallback: convert flat email list to minimal lead dicts
            emails = raw.get("found_emails", [])
            raw_url = raw.get("url")
            fallback_company = raw.get("company") or raw.get("title") or (_company_from_url(raw_url) if raw_url else None)
            leads = [
                {
                    "email": e,
                    # Derive company from email domain directly (most reliable for synthesized emails)
                    # e.g. careers@mitremedia.com -> "Mitremedia", jobs@clickhouse.com -> "Clickhouse"
                    "company": fallback_company or _company_from_url("https://" + e.split("@")[-1] if "@" in e else ""),
                    "job_title": raw.get("role") or "Recruiter / Engineering Lead",
                    "job_url": raw_url,
                    "platform": source
                }
                for e in emails
                if isinstance(e, str)
            ]

        for lead in leads:
            email = (lead.get("email") or "").strip()
            name = lead.get("name") or raw.get("name")
            company_val = lead.get("company") or _company_from_url(lead.get("job_url") or "")
            domain = _sanitize_domain(company_val) if company_val else None

            # Try to search Apollo for a Tech Lead at this company domain and enrich them
            # if we only have a generic careers/jobs email (or empty email)
            is_generic_email = not email or email.lower().startswith(("careers@", "jobs@", "info@", "hr@", "recruiting@", "recruitment@", "hello@", "contact@", "team@"))
            if is_generic_email and domain and settings.APOLLO_API_KEY:
                try:
                    tech_lead = await scraper_service.find_and_enrich_tech_lead(domain)
                    if tech_lead:
                        email = tech_lead["email"]
                        name = tech_lead["name"]
                        lead["email"] = email
                        lead["name"] = name
                        lead["job_title"] = tech_lead["job_title"]
                        lead["company"] = tech_lead["company"]
                        if tech_lead.get("linkedin_url"):
                            lead["linkedin_url"] = tech_lead["linkedin_url"]
                except Exception as e:
                    logger.debug(f"Auto Tech Lead discovery failed for {domain}: {e}")

            # Run automatic Apollo enrichment for real named contacts with generic/guessed emails
            is_real_name = name and name.lower() not in {"hiring manager", "company", "unknown", "n/a", "na", "recruiter", "team"}
            if is_real_name and domain and (not email or email.lower().startswith("careers@") or email.lower().startswith("jobs@")):
                if settings.APOLLO_API_KEY:
                    name_parts = name.strip().split(" ", 1)
                    first_name = name_parts[0]
                    last_name = name_parts[1] if len(name_parts) > 1 else ""
                    try:
                        enrich_res = await scraper_service.enrich_email_apollo(first_name, last_name, domain)
                        if enrich_res and enrich_res.get("found_emails"):
                            verified_email = enrich_res["found_emails"][0]
                            email = verified_email
                            lead["email"] = verified_email
                            if enrich_res.get("title"):
                                lead["job_title"] = enrich_res["title"]
                    except Exception as e:
                        logger.debug(f"Auto Apollo enrichment failed for {name} @ {domain}: {e}")

            if not email or not _is_quality_email(email):
                continue

            existing = await db.execute(
                select(Contact).where(Contact.user_id == user_id, Contact.email == email)
            )
            if not existing.scalar_one_or_none():
                # Derive company from lead data or URL; store None if truly unknown (never generic placeholder)
                company_val = lead.get("company") or _company_from_url(lead.get("job_url") or "")
                
                # Tag synthesized contacts from auto-discover as generic_new
                is_synthesized = source == "auto_discover" and (email.lower().startswith("careers@") or email.lower().startswith("jobs@"))
                status_val = "generic_new" if is_synthesized else "new"

                db.add(Contact(
                    user_id=user_id,
                    name=lead.get("name") or raw.get("name") or "Hiring Manager",
                    company=company_val,
                    role=lead.get("job_title") or "Recruiter / Engineering Lead",
                    source=source,
                    job_posting_url=lead.get("job_url"),   # ← JD link now populated
                    email=email,
                    status=status_val
                ))
                count += 1

        item.status = "processed"

    await db.commit()
    return count


async def run_batch_scraping(user_id: int, db: AsyncSession) -> int:
    """
    Runs career page and GitHub scraping in bulk for a target list of companies (Deactivated).
    """
    return 0
