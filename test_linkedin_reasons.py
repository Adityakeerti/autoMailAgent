import asyncio
from app.services.scrapers import scraper_service

async def main():
    print("Testing LinkedIn Scraper error diagnosis...")
    # Test with invalid cookie
    result = await scraper_service.scrape_linkedin("some_invalid_cookie_enc", "https://www.linkedin.com/in/will-gates")
    
    print("\n--- LinkedIn Scrape Result ---")
    print("Status:", result.get("status"))
    print("Reason:", result.get("reason"))
    print("Status Code:", result.get("status_code"))
    print("Found emails:", result.get("found_emails"))

if __name__ == '__main__':
    asyncio.run(main())
