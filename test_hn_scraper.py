import asyncio
import logging
from app.services.scrapers import scraper_service

logging.basicConfig(level=logging.INFO)

async def main():
    print("Testing HN Hiring Thread Scraper...")
    # Search for common tech keywords in the current month's thread
    tokens = ["rust", "python", "golang", "typescript", "react", "backend", "full stack"]
    result = await scraper_service.scrape_hn_hiring(tokens, max_comments=100)
    
    print("\n--- Scrape Results ---")
    print("Source:", result.get("source"))
    print("Found emails count:", len(result.get("found_emails", [])))
    print("Found leads count:", len(result.get("found_leads", [])))
    
    leads = result.get("found_leads", [])
    if leads:
        print("\nFirst 5 Leads Found:")
        for idx, lead in enumerate(leads[:5]):
            print(f"[{idx+1}] Email: {lead['email']}, Name: {lead['name']}, Company: {lead['company']}, URL: {lead['job_url']}")
    else:
        print("\nNo leads found. This can happen if the API request timed out or if no comments matched in the first 100 comments.")

if __name__ == '__main__':
    asyncio.run(main())
