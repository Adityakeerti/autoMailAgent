import asyncio
import logging
from app.services.scrapers import scraper_service

logging.basicConfig(level=logging.INFO)

async def main():
    print("Testing Arbeitnow matched source...")
    an_res = await scraper_service.scrape_arbeitnow(["python", "rust", "javascript", "engineer"])
    print("Arbeitnow source:", an_res.get("source"))
    print("Arbeitnow leads count:", len(an_res.get("found_leads", [])))
    if an_res.get("found_leads"):
        print("First 3 Arbeitnow leads:")
        for idx, lead in enumerate(an_res["found_leads"][:3]):
            print(f"[{idx+1}] Company: {lead['company']}, Title: {lead['job_title']}, Email: {lead['email']}, URL: {lead['job_url']}")
            
    print("\nTesting ATS direct search (Lever / Greenhouse)...")
    companies = [
        {"name": "Palantir", "domain": "palantir.com", "lever_slug": "palantir", "greenhouse_slug": ""},
        {"name": "Vercel", "domain": "vercel.com", "lever_slug": "", "greenhouse_slug": "vercel"}
    ]
    ats_res = await scraper_service.scrape_ats_direct(["engineer", "developer", "software"], companies)
    print("ATS matches found count:", len(ats_res.get("matched_jobs", [])))
    if ats_res.get("matched_jobs"):
        print("First 3 ATS matches:")
        for idx, job in enumerate(ats_res["matched_jobs"][:3]):
            print(f"[{idx+1}] Company: {job['company']}, Platform: {job['platform']}, Title: {job['job_title']}, URL: {job['job_url']}")

if __name__ == '__main__':
    asyncio.run(main())
