"""
Job Search Agent — Step 39
Multi-portal scraper that pulls job listings via HTTP (no browser required).
Portals: LinkedIn Jobs, Remotive (Indeed-equiv), Naukri, Wellfound, Arbeitnow, ATS Direct.
All results are deduplicated by job_url per user and stored in job_listings.
"""
import asyncio
import json
import logging
import os
import random
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import JobListing, JobPreference
from app.services.scrapers import _match_job, _random_ua, _safe_get, _sanitize_domain

logger = logging.getLogger("job_search")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_text(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)


def _short_desc(text: str, chars: int = 800) -> str:
    return text[:chars] if text else ""


# ---------------------------------------------------------------------------
# Per-portal search functions
# ---------------------------------------------------------------------------

async def search_linkedin_jobs(
    client: httpx.AsyncClient,
    roles: List[str],
    locations: List[str],
    experience_level: Optional[str],
    search_tokens: List[str],
) -> List[Dict[str, Any]]:
    """LinkedIn Jobs public HTTP search — returns job card data."""
    listings: List[Dict[str, Any]] = []
    exp_map = {
        "internship": "1",
        "entry": "2",
        "fresher": "2",
        "associate": "3",
    }
    f_exp = exp_map.get((experience_level or "").lower(), "2")

    for role in roles[:2]:
        for loc in locations[:2]:
            try:
                url = (
                    f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(role)}"
                    f"&location={quote_plus(loc)}&f_E={f_exp}&sortBy=DD"
                )
                resp = await _safe_get(client, url)
                if not resp:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select(".job-search-card, .base-card")
                for card in cards[:20]:
                    title_el = card.select_one(".base-search-card__title, .job-search-card__title")
                    company_el = card.select_one(".base-search-card__subtitle, .job-search-card__company-name")
                    loc_el = card.select_one(".job-search-card__location, .base-search-card__metadata")
                    link_el = card.select_one("a[href]")
                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location = loc_el.get_text(strip=True) if loc_el else loc
                    href = link_el["href"] if link_el else ""
                    if not title or not href:
                        continue
                    if not _match_job(title, "", search_tokens):
                        continue
                    job_url = href.split("?")[0] if "?" in href else href
                    listings.append({
                        "portal": "linkedin",
                        "job_title": title,
                        "company": company,
                        "location": location,
                        "job_url": job_url,
                        "description_raw": "",
                    })
                await asyncio.sleep(random.uniform(1.0, 2.0))
            except Exception as e:
                logger.debug(f"LinkedIn search error for {role}/{loc}: {e}")
    return listings


async def search_remotive_jobs(
    client: httpx.AsyncClient,
    roles: List[str],
    search_tokens: List[str],
) -> List[Dict[str, Any]]:
    """Remotive API — acts as our remote/Indeed equivalent."""
    listings: List[Dict[str, Any]] = []
    try:
        resp = await _safe_get(client, "https://remotive.com/api/remote-jobs?limit=100")
        if not resp:
            return listings
        jobs = resp.json().get("jobs", [])
        for j in jobs:
            title = j.get("title", "")
            cat = j.get("category", "")
            if not _match_job(title, cat, search_tokens):
                continue
            listings.append({
                "portal": "indeed",  # labelled as 'indeed' channel
                "job_title": title,
                "company": j.get("company_name", ""),
                "location": j.get("candidate_required_location", "Remote"),
                "job_url": j.get("url", "https://remotive.com"),
                "description_raw": _short_desc(_clean_text(j.get("description", ""))),
            })
    except Exception as e:
        logger.debug(f"Remotive search error: {e}")
    return listings


async def search_naukri_jobs(
    client: httpx.AsyncClient,
    roles: List[str],
    locations: List[str],
    search_tokens: List[str],
) -> List[Dict[str, Any]]:
    """Naukri public search — parses job cards from HTML."""
    listings: List[Dict[str, Any]] = []
    for role in roles[:2]:
        for loc in locations[:1]:
            try:
                slug_role = role.lower().replace(" ", "-")
                slug_loc = loc.lower().replace(" ", "-")
                url = f"https://www.naukri.com/{slug_role}-jobs-in-{slug_loc}"
                resp = await _safe_get(client, url)
                if not resp:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select("article.jobTuple, .srp-jobtuple-wrapper")
                for card in cards[:15]:
                    title_el = card.select_one("a.title, .row1 a")
                    company_el = card.select_one(".companyInfo .subTitle, .comp-name")
                    loc_el = card.select_one(".location span, .loc-wrap span")
                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location = loc_el.get_text(strip=True) if loc_el else loc
                    href = title_el["href"] if title_el and title_el.get("href") else ""
                    if not title or not href:
                        continue
                    if not _match_job(title, "", search_tokens):
                        continue
                    listings.append({
                        "portal": "naukri",
                        "job_title": title,
                        "company": company,
                        "location": location,
                        "job_url": href,
                        "description_raw": "",
                    })
                await asyncio.sleep(random.uniform(1.5, 3.0))
            except Exception as e:
                logger.debug(f"Naukri search error for {role}/{loc}: {e}")
    return listings


async def search_wellfound_jobs(
    client: httpx.AsyncClient,
    roles: List[str],
    search_tokens: List[str],
) -> List[Dict[str, Any]]:
    """Wellfound (YC/AngelList) — parse startup jobs from public search."""
    listings: List[Dict[str, Any]] = []
    for role in roles[:2]:
        try:
            url = f"https://wellfound.com/jobs?q={quote_plus(role)}&remote=true"
            resp = await _safe_get(client, url)
            if not resp:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            # Wellfound renders job cards with data attributes
            cards = soup.select("[data-test='JobListing'], .job-listing, .styles_component__L6Pq8")
            for card in cards[:15]:
                title_el = card.select_one("h2, .role, [data-test='JobListingTitle']")
                company_el = card.select_one(".startup-link, [data-test='CompanyName']")
                link_el = card.select_one("a[href*='/jobs/']")
                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                href = link_el["href"] if link_el else ""
                if not title or not href:
                    continue
                if not _match_job(title, "", search_tokens):
                    continue
                job_url = f"https://wellfound.com{href}" if href.startswith("/") else href
                listings.append({
                    "portal": "wellfound",
                    "job_title": title,
                    "company": company,
                    "location": "Remote",
                    "job_url": job_url,
                    "description_raw": "",
                })
            await asyncio.sleep(random.uniform(1.0, 2.0))
        except Exception as e:
            logger.debug(f"Wellfound search error for {role}: {e}")
    return listings


async def search_arbeitnow_jobs(
    client: httpx.AsyncClient,
    search_tokens: List[str],
) -> List[Dict[str, Any]]:
    """Arbeitnow public API — always-on general portal."""
    listings: List[Dict[str, Any]] = []
    try:
        resp = await _safe_get(client, "https://www.arbeitnow.com/api/job-board-api")
        if not resp:
            return listings
        for job in resp.json().get("data", []):
            title = job.get("title", "")
            tags_str = ", ".join(job.get("tags", []))
            if not _match_job(title, tags_str, search_tokens):
                continue
            listings.append({
                "portal": "general",
                "job_title": title,
                "company": job.get("company_name", ""),
                "location": job.get("location", "Remote"),
                "job_url": job.get("url", "https://www.arbeitnow.com"),
                "description_raw": _short_desc(_clean_text(job.get("description", ""))),
            })
    except Exception as e:
        logger.debug(f"Arbeitnow search error: {e}")
    return listings


async def search_ats_direct_jobs(
    client: httpx.AsyncClient,
    search_tokens: List[str],
) -> List[Dict[str, Any]]:
    """Lever + Greenhouse ATS direct job board search using target_sources.json."""
    listings: List[Dict[str, Any]] = []
    try:
        sources_path = os.path.join(os.getcwd(), "target_sources.json")
        if not os.path.exists(sources_path):
            return listings
        with open(sources_path) as f:
            companies = json.load(f).get("companies", [])

        for comp in companies:
            cname = comp.get("name", "")
            lever = comp.get("lever_slug", "")
            greenhouse = comp.get("greenhouse_slug", "")
            loc = comp.get("location", "Remote")

            if lever:
                try:
                    resp = await _safe_get(client, f"https://api.lever.co/v0/postings/{lever}?mode=json")
                    if resp:
                        for post in resp.json():
                            title = post.get("text", "")
                            dept = post.get("categories", {}).get("department", "")
                            if _match_job(title, dept, search_tokens):
                                listings.append({
                                    "portal": "general",
                                    "job_title": title,
                                    "company": cname,
                                    "location": loc,
                                    "job_url": post.get("hostedUrl") or post.get("applyUrl", ""),
                                    "description_raw": _short_desc(post.get("descriptionPlain", "")),
                                })
                except Exception as e:
                    logger.debug(f"Lever ATS error for {cname}: {e}")

            if greenhouse:
                try:
                    resp = await _safe_get(
                        client,
                        f"https://boards-api.greenhouse.io/v1/boards/{greenhouse}/jobs?content=true"
                    )
                    if resp:
                        for job in resp.json().get("jobs", []):
                            title = job.get("title", "")
                            depts = ", ".join(d.get("name", "") for d in job.get("departments", []))
                            if _match_job(title, depts, search_tokens):
                                listings.append({
                                    "portal": "general",
                                    "job_title": title,
                                    "company": cname,
                                    "location": loc,
                                    "job_url": job.get("absolute_url", ""),
                                    "description_raw": _short_desc(
                                        _clean_text(job.get("content", ""))
                                    ),
                                })
                except Exception as e:
                    logger.debug(f"Greenhouse ATS error for {cname}: {e}")
    except Exception as e:
        logger.debug(f"ATS direct search error: {e}")
    return listings


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

async def run_job_search(user_id: int, db: AsyncSession) -> Dict[str, Any]:
    """
    Orchestrator for the Job Search Agent.
    1. Reads user's JobPreference (roles, locations, experience_level).
    2. Expands role keywords via LLM service.
    3. Fans out to all portals concurrently.
    4. Deduplicates by job_url (skips URLs already in job_listings for this user).
    5. Writes new listings to job_listings with status='new'.
    Returns summary stats.
    """
    from app.services.llm import llm_service

    # Load preferences
    res = await db.execute(select(JobPreference).where(JobPreference.user_id == user_id))
    jp = res.scalar_one_or_none()
    if not jp or not any([jp.role_1, jp.role_2, jp.role_3]):
        return {"error": "No job preferences set. Please add at least one target role."}

    roles = [r for r in [jp.role_1, jp.role_2, jp.role_3] if r]
    locations_raw = jp.locations or "India"
    locations = [l.strip() for l in locations_raw.split(",") if l.strip()][:3]
    exp_level = jp.experience_level or "entry"

    # Expand keywords
    all_tokens: List[str] = []
    for role in roles:
        expanded = await llm_service.expand_role_keywords(role)
        all_tokens.extend([k.lower() for k in expanded])
    all_tokens = list(dict.fromkeys(all_tokens))  # dedupe while preserving order

    # Fetch existing URLs for this user to avoid duplicates
    existing_res = await db.execute(
        select(JobListing.job_url).where(JobListing.user_id == user_id)
    )
    existing_urls: set = set(existing_res.scalars().all())

    portals_hit: List[str] = []
    raw_listings: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        tasks = {
            "linkedin": search_linkedin_jobs(client, roles, locations, exp_level, all_tokens),
            "remotive": search_remotive_jobs(client, roles, all_tokens),
            "naukri": search_naukri_jobs(client, roles, locations, all_tokens),
            "wellfound": search_wellfound_jobs(client, roles, all_tokens),
            "arbeitnow": search_arbeitnow_jobs(client, all_tokens),
            "ats_direct": search_ats_direct_jobs(client, all_tokens),
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    for (portal, _), result in zip(tasks.items(), results):
        if isinstance(result, Exception):
            logger.warning(f"Portal {portal} search raised: {result}")
            continue
        if result:
            portals_hit.append(portal)
            raw_listings.extend(result)

    # Deduplicate by job_url
    seen_urls: set = set()
    new_listings: List[Dict[str, Any]] = []
    for listing in raw_listings:
        url = listing.get("job_url", "").strip()
        if not url or url in existing_urls or url in seen_urls:
            continue
        seen_urls.add(url)
        new_listings.append(listing)

    # Write to DB
    saved = 0
    for listing in new_listings:
        jl = JobListing(
            user_id=user_id,
            portal=listing["portal"],
            job_title=listing["job_title"],
            company=listing.get("company"),
            location=listing.get("location"),
            description_raw=listing.get("description_raw"),
            job_url=listing["job_url"],
            status="new",
        )
        db.add(jl)
        saved += 1

    await db.commit()

    logger.info(f"Job search for user {user_id}: found {len(raw_listings)}, new {saved}, portals {portals_hit}")
    return {
        "found": len(raw_listings),
        "new": saved,
        "portals_hit": portals_hit,
        "roles_searched": roles,
    }
