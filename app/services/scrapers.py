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
        """Scrape static HTML career page for contact emails and role details"""
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await _safe_get(client, url)
            if not resp:
                return {"source": "career_page", "url": url, "title": "Career Page", "found_emails": [], "found_leads": []}
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")
            title = soup.title.string.strip() if soup.title and soup.title.string else "Career Page"
            emails = [e for e in extract_public_emails(html) if _is_quality_email(e)]
            leads = [{"email": e, "company": title, "job_title": "Recruiter", "job_url": url, "platform": "career_page"} for e in emails]
            return {
                "source": "career_page",
                "url": url,
                "title": title,
                "found_emails": emails,
                "found_leads": leads,
                "raw_text": soup.get_text()[:2000]
            }

    async def scrape_github(self, username_or_repo: str) -> Dict[str, Any]:
        """Scrape public GitHub user bio or README for email"""
        url = f"https://api.github.com/users/{username_or_repo}"
        headers = {"User-Agent": "AutoMail-Bot"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    email = data.get("email")
                    bio = data.get("bio", "") or ""
                    raw_emails = [email] if email else extract_public_emails(bio)
                    emails = [e for e in raw_emails if e and _is_quality_email(e)]
                    profile_url = data.get("html_url", f"https://github.com/{username_or_repo}")
                    company = data.get("company") or username_or_repo
                    leads = [{"email": e, "company": company, "job_title": "Developer", "job_url": profile_url, "platform": "github"} for e in emails]
                    return {
                        "source": "github",
                        "url": profile_url,
                        "name": data.get("name") or username_or_repo,
                        "company": company,
                        "found_emails": [e for e in emails if e],
                        "found_leads": leads,
                        "raw_data": data
                    }
            except Exception:
                pass

            web_url = f"https://github.com/{username_or_repo}"
            w_resp = await _safe_get(client, web_url)
            emails = [e for e in extract_public_emails(w_resp.text) if _is_quality_email(e)] if w_resp else []
            leads = [{"email": e, "company": username_or_repo, "job_title": "Developer", "job_url": web_url, "platform": "github"} for e in emails]
            return {"source": "github", "url": web_url, "name": username_or_repo, "found_emails": emails, "found_leads": leads}

    async def scrape_job_portal(self, url: str) -> Dict[str, Any]:
        """Scrape job portal listing for emails"""
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await _safe_get(client, url)
            if not resp:
                return {"source": "job_portal", "url": url, "found_emails": [], "found_leads": []}
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")
            emails = [e for e in extract_public_emails(html) if _is_quality_email(e)]
            company = _extract_company_from_page(soup, url)
            leads = [{"email": e, "company": company, "job_title": "Recruiter", "job_url": url, "platform": "job_portal"} for e in emails]
            return {
                "source": "job_portal",
                "url": url,
                "company": company,
                "found_emails": emails,
                "found_leads": leads,
                "raw_text": soup.get_text()[:2000]
            }

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
        Multi-Source Auto-Discover Job Scraper (Keyword-Agnostic with LLM Expansion Layer).

        Quality-first approach:
        - Filters out free consumer email domains and known job-board / ATS domains
        - Attaches per-email job posting URL so contacts get a clickable JD link
        - Caps output to top 15 highest-quality new leads per run
        - Returns empty result (no DB write) if no NEW leads are found
        """
        from app.services.llm import llm_service

        res = await db.execute(select(JobPreference).where(JobPreference.user_id == user_id))
        jp = res.scalar_one_or_none()

        if not jp or not any([jp.role_1, jp.role_2, jp.role_3]):
            return {"error": "No job preferences set. Please set at least one target role in Resume & Context."}

        roles = [r for r in [jp.role_1, jp.role_2, jp.role_3] if r]
        locations = jp.locations or "India"
        location_list = [l.strip() for l in locations.split(",")]
        primary_location = location_list[0] if location_list else "India"

        cookie = settings.SHARED_LINKEDIN_COOKIE
        all_results = []
        # Rich per-email leads list: {"email", "company", "job_title", "job_url", "platform"}
        all_leads: List[Dict[str, Any]] = []
        expanded_role_map = {}

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            # 1. Fetch Jobicy Open Job Directory API (High Yield Tech Jobs)
            jobicy_resp = await _safe_get(client, "https://jobicy.com/api/v2/remote-jobs?count=100")
            jobicy_jobs = jobicy_resp.json().get("jobs", []) if jobicy_resp else []

            # 2. Fetch Remotive Tech Jobs API
            remotive_resp = await _safe_get(client, "https://remotive.com/api/remote-jobs?limit=50")
            remotive_jobs = remotive_resp.json().get("jobs", []) if remotive_resp else []

            for role in roles:
                role_clean = role.strip()
                # Expand role into synonyms & acronyms
                expanded_kw = await llm_service.expand_role_keywords(role_clean)
                expanded_role_map[role_clean] = expanded_kw

                role_encoded = role_clean.replace(" ", "%20")
                location_encoded = primary_location.replace(" ", "%20")
                search_tokens = [k.lower() for k in expanded_kw]

                # --- Source A: LinkedIn Jobs Search ---
                try:
                    li_url = f"https://www.linkedin.com/jobs/search/?keywords={role_encoded}&location={location_encoded}"
                    li_headers = {}
                    if cookie:
                        li_headers["Cookie"] = f"li_at={cookie}"
                    li_resp = await _safe_get(client, li_url, headers=li_headers)
                    if li_resp:
                        soup = BeautifulSoup(li_resp.text, "html.parser")

                        # Extract company names from LinkedIn cards
                        companies = [
                            el.get_text(strip=True)
                            for el in soup.select(".base-search-card__subtitle")
                            if el.get_text(strip=True)
                        ][:10]

                        li_leads = []
                        for comp in companies:
                            comp_domain = _sanitize_domain(comp)
                            if comp_domain and _is_quality_email(f"careers@{comp_domain}"):
                                li_leads.append({
                                    "email": f"careers@{comp_domain}",
                                    "company": comp,
                                    "job_title": role_clean,
                                    "job_url": li_url,  # LinkedIn search page (best we can get without auth)
                                    "platform": "linkedin_jobs"
                                })

                        all_leads.extend(li_leads)
                        all_results.append({
                            "platform": "linkedin_jobs",
                            "role": role_clean,
                            "expanded_keywords": expanded_kw,
                            "location": primary_location,
                            "url": li_url,
                            "found_emails": [l["email"] for l in li_leads],
                            "companies_found": companies
                        })
                except Exception as e:
                    logger.debug(f"LinkedIn auto-discover error for {role_clean}: {e}")

                # --- Source B: Jobicy Job Matcher (Keyword-Agnostic) ---
                try:
                    matched_jobicy = [
                        j for j in jobicy_jobs
                        if _match_job(j.get("jobTitle"), j.get("jobCategory"), search_tokens)
                    ]
                    jobicy_leads = []
                    jobicy_comps = []
                    for j in matched_jobicy[:10]:
                        cname = j.get("companyName", "")
                        job_title = j.get("jobTitle", role_clean)
                        # Use the real Jobicy job URL if available
                        job_url = j.get("url") or j.get("jobExcerpt") or "https://jobicy.com"
                        if cname:
                            jobicy_comps.append(cname)
                            c_domain = _sanitize_domain(cname)
                            if c_domain:
                                for prefix in ["careers", "jobs"]:
                                    email = f"{prefix}@{c_domain}"
                                    if _is_quality_email(email):
                                        jobicy_leads.append({
                                            "email": email,
                                            "company": cname,
                                            "job_title": job_title,
                                            "job_url": job_url,
                                            "platform": "jobicy"
                                        })

                    all_leads.extend(jobicy_leads)
                    if matched_jobicy:
                        all_results.append({
                            "platform": "jobicy",
                            "role": role_clean,
                            "expanded_keywords": expanded_kw,
                            "found_emails": [l["email"] for l in jobicy_leads],
                            "companies_found": jobicy_comps
                        })
                except Exception as e:
                    logger.debug(f"Jobicy auto-discover error for {role_clean}: {e}")

                # --- Source C: Remotive Job Matcher (Keyword-Agnostic) ---
                try:
                    matched_remotive = [
                        j for j in remotive_jobs
                        if _match_job(j.get("title"), j.get("category"), search_tokens)
                    ]
                    remotive_leads = []
                    remotive_comps = []
                    for j in matched_remotive[:10]:
                        cname = j.get("company_name", "")
                        job_title = j.get("title", role_clean)
                        # Remotive provides a direct job URL
                        job_url = j.get("url") or "https://remotive.com"
                        if cname:
                            remotive_comps.append(cname)
                            c_domain = _sanitize_domain(cname)
                            if c_domain:
                                email = f"careers@{c_domain}"
                                if _is_quality_email(email):
                                    remotive_leads.append({
                                        "email": email,
                                        "company": cname,
                                        "job_title": job_title,
                                        "job_url": job_url,
                                        "platform": "remotive"
                                    })

                    all_leads.extend(remotive_leads)
                    if matched_remotive:
                        all_results.append({
                            "platform": "remotive",
                            "role": role_clean,
                            "expanded_keywords": expanded_kw,
                            "found_emails": [l["email"] for l in remotive_leads],
                            "companies_found": remotive_comps
                        })
                except Exception as e:
                    logger.debug(f"Remotive auto-discover error for {role_clean}: {e}")

                await asyncio.sleep(0.5)  # Human-pace delay between roles

            # --- Source D: HN Hiring Thread (Keyword-Agnostic with expanded synonyms) ---
            try:
                # Compile all expanded synonyms from roles to search in HN comments
                all_tokens = []
                for role_clean, expanded in expanded_role_map.items():
                    all_tokens.extend([k.lower() for k in expanded])
                
                # Fetch HN top comments
                hn_result = await self.scrape_hn_hiring(all_tokens, max_comments=45)
                hn_leads = hn_result.get("found_leads", [])
                if hn_leads:
                    # Map the matched role back to the user's preferred roles
                    for lead in hn_leads:
                        clean_text_to_match = f"{lead.get('job_title', '')} {lead.get('company', '')}"
                        matched_role = roles[0]
                        for role_clean, expanded in expanded_role_map.items():
                            search_tokens = [k.lower() for k in expanded]
                            if _match_job(clean_text_to_match, "", search_tokens):
                                matched_role = role_clean
                                break
                        lead["job_title"] = matched_role
                    
                    all_leads.extend(hn_leads)
                    all_results.append({
                        "platform": "hn_hiring",
                        "role": "HN Matching Roles",
                        "expanded_keywords": all_tokens,
                        "found_emails": hn_result.get("found_emails", []),
                        "companies_found": [l["company"] for l in hn_leads]
                    })
            except Exception as e:
                logger.debug(f"HN hiring auto-discover error: {e}")

            # --- Source E: Arbeitnow Job Matcher (Keyword-Agnostic with expanded synonyms) ---
            try:
                all_tokens = []
                for role_clean, expanded in expanded_role_map.items():
                    all_tokens.extend([k.lower() for k in expanded])
                
                arbeitnow_result = await self.scrape_arbeitnow(all_tokens)
                arbeitnow_leads = arbeitnow_result.get("found_leads", [])
                if arbeitnow_leads:
                    for lead in arbeitnow_leads:
                        clean_text_to_match = f"{lead.get('job_title', '')} {lead.get('company', '')}"
                        matched_role = roles[0]
                        for role_clean, expanded in expanded_role_map.items():
                            search_tokens = [k.lower() for k in expanded]
                            if _match_job(clean_text_to_match, "", search_tokens):
                                matched_role = role_clean
                                break
                        lead["job_title"] = matched_role
                    
                    all_leads.extend(arbeitnow_leads)
                    all_results.append({
                        "platform": "arbeitnow",
                        "role": "Arbeitnow Matching Roles",
                        "expanded_keywords": all_tokens,
                        "found_emails": arbeitnow_result.get("found_emails", []),
                        "companies_found": [l["company"] for l in arbeitnow_leads]
                    })
            except Exception as e:
                logger.debug(f"Arbeitnow auto-discover error: {e}")

            # --- Source F: ATS Direct Search (Lever & Greenhouse) ---
            try:
                import json
                import os
                target_companies = []
                if os.path.exists("target_sources.json"):
                    with open("target_sources.json", "r") as f:
                        target_data = json.load(f)
                        target_companies = target_data.get("companies", [])
                
                if target_companies:
                    all_tokens = []
                    for role_clean, expanded in expanded_role_map.items():
                        all_tokens.extend([k.lower() for k in expanded])
                    
                    ats_result = await self.scrape_ats_direct(all_tokens, target_companies)
                    matched_jobs = ats_result.get("matched_jobs", [])
                    if matched_jobs:
                        all_results.append({
                            "platform": "ats_direct",
                            "role": "ATS Matching Roles",
                            "expanded_keywords": all_tokens,
                            "found_emails": [],
                            "companies_found": [j["company"] for j in matched_jobs],
                            "matched_jobs": matched_jobs
                        })
            except Exception as e:
                logger.debug(f"ATS direct search auto-discover error: {e}")

        # --- Deduplication: filter against existing contacts AND existing queue ---
        existing_contact_res = await db.execute(
            select(Contact.email).where(Contact.user_id == user_id)
        )
        existing_contact_emails = set(e.lower() for e in existing_contact_res.scalars().all())

        # Check ALL queue entries (pending + processed) to prevent duplicate batches on rapid re-runs
        existing_queue_res = await db.execute(
            select(ScrapeQueue.raw_data).where(ScrapeQueue.user_id == user_id)
        )
        known_queue_emails: set = set()
        for q_item in existing_queue_res.scalars().all():
            if isinstance(q_item, str):
                try:
                    import json
                    q_item = json.loads(q_item)
                except Exception:
                    pass
            if isinstance(q_item, dict):
                for lead in q_item.get("found_leads", []):
                    if isinstance(lead, dict) and lead.get("email"):
                        known_queue_emails.add(lead["email"].lower())
                # Also check legacy flat found_emails list
                for e in q_item.get("found_emails", []):
                    if isinstance(e, str):
                        known_queue_emails.add(e.lower())


        all_known_emails = existing_contact_emails.union(known_queue_emails)

        # Deduplicate leads by email address, keeping first occurrence
        seen_emails: set = set()
        unique_leads: List[Dict[str, Any]] = []
        for lead in all_leads:
            email_lower = lead["email"].lower()
            if email_lower not in all_known_emails and email_lower not in seen_emails:
                seen_emails.add(email_lower)
                unique_leads.append(lead)

        # Quality cap: top 15 leads max per run
        unique_leads = unique_leads[:15]

        # Flat email list for backward-compatible display in scrape queue table
        unique_emails = [l["email"] for l in unique_leads]

        return {
            "source": "auto_discover",
            "roles_searched": roles,
            "expanded_keywords_by_role": expanded_role_map,
            "location": primary_location,
            "platforms_searched": ["linkedin_jobs", "jobicy", "remotive", "hn_hiring", "arbeitnow", "ats_direct"],
            "found_emails": unique_emails,
            "found_leads": unique_leads,        # Rich per-email metadata with job URLs
            "results_by_platform": all_results,
            "total_unique_emails": len(unique_leads)
        }

    async def enrich_email_apollo(self, first_name: str, last_name: str, company_domain: str) -> Dict[str, Any]:
        """Uses Apollo.io people/match API to find a verified email."""
        if not settings.APOLLO_API_KEY:
            return {"error": "Apollo.io API key not configured. Add APOLLO_API_KEY to .env"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.apollo.io/v1/people/match",
                    headers={"x-api-key": settings.APOLLO_API_KEY, "Content-Type": "application/json"},
                    json={
                        "first_name": first_name,
                        "last_name": last_name,
                        "organization_domain": company_domain,
                        "reveal_personal_emails": False
                    }
                )
                data = resp.json()

            person = data.get("person") or {}
            email = person.get("email")
            leads = []
            if email and _is_quality_email(email):
                leads.append({
                    "email": email,
                    "company": person.get("organization", {}).get("name") or company_domain,
                    "job_title": person.get("title") or "Contact",
                    "job_url": None,
                    "platform": "apollo"
                })
            return {
                "source": "apollo",
                "found_emails": [email] if email else [],
                "found_leads": leads,
                "name": f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
                "title": person.get("title"),
                "company": person.get("organization", {}).get("name")
            }
        except Exception as e:
            return {"error": f"Apollo.io request failed: {str(e)}"}

    async def find_and_enrich_tech_lead(self, company_domain: str) -> Optional[Dict[str, Any]]:
        """
        Searches Apollo for a tech leader/engineering manager at the company domain
        and enriches their email.
        """
        if not settings.APOLLO_API_KEY:
            return None

        titles = [
            "Tech Lead", "Engineering Manager", "Technical Lead", "CTO", 
            "Director of Engineering", "VP of Engineering", "Software Engineering Manager", 
            "Lead Software Engineer", "Staff Software Engineer", "Principal Software Engineer"
        ]
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                search_url = "https://api.apollo.io/api/v1/mixed_people/api_search"
                headers = {
                    "x-api-key": settings.APOLLO_API_KEY, 
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache"
                }
                payload = {
                    "q_organization_domains_list": [company_domain],
                    "person_titles": titles,
                    "per_page": 5
                }
                
                logger.info(f"Searching Apollo for tech leads at {company_domain}")
                resp = await client.post(search_url, headers=headers, json=payload)
                if resp.status_code != 200:
                    logger.warning(f"Apollo search failed with status {resp.status_code}: {resp.text}")
                    return None
                    
                data = resp.json()
                people = data.get("people") or []
                if not people:
                    logger.info(f"No tech leads found on Apollo for {company_domain}")
                    return None
                
                for person in people:
                    first_name = person.get("first_name")
                    last_name = person.get("last_name")
                    if first_name and last_name:
                        logger.info(f"Attempting to enrich Apollo email for {first_name} {last_name} at {company_domain}")
                        enrich_res = await self.enrich_email_apollo(first_name, last_name, company_domain)
                        if enrich_res and enrich_res.get("found_emails"):
                            email = enrich_res["found_emails"][0]
                            return {
                                "email": email,
                                "name": f"{first_name} {last_name}".strip(),
                                "job_title": person.get("title") or "Tech Lead",
                                "company": person.get("organization", {}).get("name") or company_domain,
                                "linkedin_url": person.get("linkedin_url"),
                                "platform": "apollo"
                            }
        except Exception as e:
            logger.error(f"Failed to find and enrich tech lead at {company_domain}: {e}")
            
        return None

    async def scrape_hn_hiring(self, search_tokens: List[str], max_comments: int = 50) -> Dict[str, Any]:
        """
        Scrapes the latest HN 'Who is Hiring' thread, parses comments for matching keywords,
        and extracts named contacts with emails.
        """
        found_leads = []
        emails_found = []
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            # 1. Fetch submitted items of user 'whoishiring'
            user_url = "https://hacker-news.firebaseio.com/v0/user/whoishiring.json"
            user_resp = await _safe_get(client, user_url)
            if not user_resp:
                return {"source": "hn_hiring", "found_emails": [], "found_leads": []}
            
            submitted = user_resp.json().get("submitted", [])
            if not submitted:
                return {"source": "hn_hiring", "found_emails": [], "found_leads": []}
            
            # Find the latest "Who is hiring?" story
            story_id = None
            for item_id in submitted[:10]:
                item_url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
                item_resp = await _safe_get(client, item_url)
                if item_resp:
                    item_data = item_resp.json()
                    title = item_data.get("title", "")
                    if item_data.get("type") == "story" and "who is hiring" in title.lower():
                        story_id = item_id
                        break
            
            if not story_id:
                logger.warning("Could not find latest HN 'Who is Hiring' story.")
                return {"source": "hn_hiring", "found_emails": [], "found_leads": []}
            
            # Fetch the story kids (top-level comments)
            story_resp = await _safe_get(client, f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
            if not story_resp:
                return {"source": "hn_hiring", "found_emails": [], "found_leads": []}
            
            kids = story_resp.json().get("kids", [])
            if not kids:
                return {"source": "hn_hiring", "found_emails": [], "found_leads": []}
            
            # Fetch comments in parallel up to max_comments
            comment_ids = kids[:max_comments]
            tasks = []
            for cid in comment_ids:
                tasks.append(_safe_get(client, f"https://hacker-news.firebaseio.com/v0/item/{cid}.json"))
            
            resps = await asyncio.gather(*tasks)
            comments = [r.json() for r in resps if r]
            
            # Prepare matchers
            for comment in comments:
                if not comment or comment.get("deleted") or comment.get("dead"):
                    continue
                text = comment.get("text", "")
                if not text:
                    continue
                
                # Convert HTML text to clean plain text for matching and parsing
                clean_text = BeautifulSoup(text, "html.parser").get_text()
                
                # Reuse _match_job logic
                if _match_job(clean_text, "", search_tokens):
                    # Extract emails
                    emails = extract_public_emails(text)
                    if not emails:
                        continue
                        
                    # Find company name
                    first_line = clean_text.split("\n")[0].strip()
                    parts = first_line.split("|")
                    company = parts[0].strip() if parts else "Unknown Company"
                    company = re.sub(r'\s*\([^)]*\)', '', company).strip()
                    
                    for e in emails:
                        if not _is_quality_email(e):
                            continue
                        name = _extract_name_from_comment(clean_text, e)
                        emails_found.append(e)
                        
                        job_url = f"https://news.ycombinator.com/item?id={comment.get('id')}"
                        
                        found_leads.append({
                            "email": e,
                            "name": name,
                            "company": company,
                            "job_title": "Software Engineer",
                            "job_url": job_url,
                            "platform": "hn_hiring"
                        })
                        
        return {
            "source": "hn_hiring",
            "found_emails": emails_found,
            "found_leads": found_leads
        }

    async def scrape_arbeitnow(self, search_tokens: List[str]) -> Dict[str, Any]:
        """Scrape Arbeitnow API for matching job postings."""
        found_leads = []
        emails_found = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await _safe_get(client, "https://www.arbeitnow.com/api/job-board-api")
            if resp:
                data = resp.json().get("data", [])
                for job in data:
                    title = job.get("title", "")
                    tags_str = ", ".join(job.get("tags", []))
                    if _match_job(title, tags_str, search_tokens):
                        cname = job.get("company_name", "")
                        desc = job.get("description", "")
                        job_url = job.get("url") or "https://www.arbeitnow.com"
                        
                        emails = extract_public_emails(desc)
                        if emails:
                            for e in emails:
                                if _is_quality_email(e):
                                    emails_found.append(e)
                                    found_leads.append({
                                        "email": e,
                                        "name": "Hiring Manager",
                                        "company": cname,
                                        "job_title": title,
                                        "job_url": job_url,
                                        "platform": "arbeitnow"
                                    })
                        else:
                            c_domain = _sanitize_domain(cname)
                            if c_domain:
                                email = f"careers@{c_domain}"
                                if _is_quality_email(email):
                                    emails_found.append(email)
                                    found_leads.append({
                                        "email": email,
                                        "name": "Hiring Manager",
                                        "company": cname,
                                        "job_title": title,
                                        "job_url": job_url,
                                        "platform": "arbeitnow"
                                    })
        return {
            "source": "arbeitnow",
            "found_emails": emails_found,
            "found_leads": found_leads
        }

    async def scrape_ats_direct(self, search_tokens: List[str], companies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Scrapes Lever and Greenhouse directly for job postings matching roles.
        Returns a list of matched jobs.
        """
        matched_jobs = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            for comp in companies:
                cname = comp.get("name")
                domain = comp.get("domain")
                lever = comp.get("lever_slug")
                greenhouse = comp.get("greenhouse_slug")
                
                if lever:
                    try:
                        url = f"https://api.lever.co/v0/postings/{lever}?mode=json"
                        resp = await _safe_get(client, url)
                        if resp:
                            postings = resp.json()
                            for post in postings:
                                title = post.get("text", "")
                                categories = post.get("categories", {})
                                dept = categories.get("department", "") or categories.get("team", "")
                                if _match_job(title, dept, search_tokens):
                                    matched_jobs.append({
                                        "company": cname,
                                        "domain": domain,
                                        "job_title": title,
                                        "job_url": post.get("hostedUrl") or post.get("applyUrl"),
                                        "platform": "lever"
                                    })
                    except Exception as e:
                        logger.debug(f"Lever search failed for {cname}: {e}")
                
                if greenhouse:
                    try:
                        url = f"https://boards-api.greenhouse.io/v1/boards/{greenhouse}/jobs?content=true"
                        resp = await _safe_get(client, url)
                        if resp:
                            jobs_list = resp.json().get("jobs", [])
                            for job in jobs_list:
                                title = job.get("title", "")
                                depts = ", ".join([d.get("name", "") for d in job.get("departments", [])])
                                if _match_job(title, depts, search_tokens):
                                    matched_jobs.append({
                                        "company": cname,
                                        "domain": domain,
                                        "job_title": title,
                                        "job_url": job.get("absolute_url"),
                                        "platform": "greenhouse"
                                    })
                    except Exception as e:
                        logger.debug(f"Greenhouse search failed for {cname}: {e}")
                        
        return {
            "source": "ats_direct",
            "matched_jobs": matched_jobs
        }


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
    Runs career page and GitHub scraping in bulk for a target list of companies.
    Iterates the user-maintained list from target_sources.json.
    """
    import json
    import os
    
    target_companies = []
    if os.path.exists("target_sources.json"):
        try:
            with open("target_sources.json", "r") as f:
                target_data = json.load(f)
                target_companies = target_data.get("companies", [])
        except Exception as e:
            logger.error(f"Failed to load target_sources.json for batch: {e}")
            return 0

    new_items_count = 0
    for comp in target_companies:
        career = comp.get("career_page")
        github = comp.get("github_org")
        cname = comp.get("name")
        
        if career:
            try:
                result = await scraper_service.scrape_career_page(career)
                if result.get("found_emails"):
                    item = ScrapeQueue(
                        user_id=user_id,
                        source="career_page",
                        raw_data=result,
                        status="pending"
                    )
                    db.add(item)
                    new_items_count += 1
            except Exception as e:
                logger.error(f"Batch scrape career page failed for {cname}: {e}")
                
        if github:
            try:
                result = await scraper_service.scrape_github(github)
                if result.get("found_emails"):
                    item = ScrapeQueue(
                        user_id=user_id,
                        source="github",
                        raw_data=result,
                        status="pending"
                    )
                    db.add(item)
                    new_items_count += 1
            except Exception as e:
                logger.error(f"Batch scrape github failed for {cname}: {e}")
                
    if new_items_count > 0:
        await db.commit()
        normalized_count = await normalize_scrape_queue(user_id, db)
        logger.info(f"Batch scraping completed. Added {normalized_count} contacts.")
        return normalized_count
        
    return 0
