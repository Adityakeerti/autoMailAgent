import asyncio
import os
import shutil
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import AsyncSessionLocal
from app.models import Contact, ScrapeQueue, Setting, User
from app.services.scrapers import run_batch_scraping

async def main():
    print("Setting up mock target_sources.json for batch scraping test...")
    # Backup original target_sources.json if it exists
    backup_exists = os.path.exists("target_sources.json")
    if backup_exists:
        shutil.copy("target_sources.json", "target_sources.json.bak")
        
    # Write a test target sources file with a single fast-responding configuration
    # We use a known small GitHub organization or a fast site
    import json
    test_sources = {
        "companies": [
            {
                "name": "Stitch",
                "domain": "stitch.io",
                "career_page": "",
                "github_org": "stitch-mcp", # a simple org that compiles fast or return no emails safely
                "lever_slug": "",
                "greenhouse_slug": ""
            }
        ]
    }
    with open("target_sources.json", "w") as f:
        json.dump(test_sources, f)
        
    test_email = "batch_test@example.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Sign up or login
        res = await client.post("/auth/signup", json={"email": test_email, "password": "Password123!"})
        if res.status_code == 201:
            token = res.json()["access_token"]
        else:
            res = await client.post("/auth/login", json={"email": test_email, "password": "Password123!"})
            token = res.json()["access_token"]
            
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            user_res = await db.execute(select(User).where(User.email == test_email))
            user = user_res.scalar_one_or_none()
            user_id = user.id
            
            print("Triggering batch scraping via endpoint...")
            headers = {"Authorization": f"Bearer {token}"}
            batch_res = await client.post("/scrapers/batch", headers=headers)
            print("Response:", batch_res.status_code, batch_res.json())
            assert batch_res.status_code == 200
            
            # Clean up test user data
            from sqlalchemy import delete
            from app.models import Template
            await db.execute(delete(Contact).where(Contact.user_id == user_id))
            await db.execute(delete(ScrapeQueue).where(ScrapeQueue.user_id == user_id))
            await db.execute(delete(Setting).where(Setting.user_id == user_id))
            await db.execute(delete(Template).where(Template.user_id == user_id))
            await db.execute(delete(User).where(User.id == user_id))
            await db.commit()
            
    # Restore original target_sources.json
    if backup_exists:
        shutil.copy("target_sources.json.bak", "target_sources.json")
        os.remove("target_sources.json.bak")
    else:
        if os.path.exists("target_sources.json"):
            os.remove("target_sources.json")
            
    print("Batch scraping test passed successfully!")

if __name__ == '__main__':
    asyncio.run(main())
