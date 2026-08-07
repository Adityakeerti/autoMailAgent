import asyncio
import random
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import AsyncSessionLocal
from app.models import Contact, ScrapeQueue, Setting
from app.services.scrapers import normalize_scrape_queue

async def main():
    email_suffix = str(random.randint(1000, 9999))
    test_email = f"apollo_test_{email_suffix}@example.com"
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Sign up or login
        res = await client.post("/auth/signup", json={"email": test_email, "password": "Password123!"})
        if res.status_code == 201:
            token = res.json()["access_token"]
        else:
            res = await client.post("/auth/login", json={"email": test_email, "password": "Password123!"})
            token = res.json()["access_token"]
        
        # Find user ID from database
        async with AsyncSessionLocal() as db:
            from app.models import User
            from sqlalchemy import select
            user_res = await db.execute(select(User).where(User.email == test_email))
            user = user_res.scalar_one_or_none()
            user_id = user.id
            
            # Create a pending scrape queue item with a named lead having a generic email
            q_item = ScrapeQueue(
                user_id=user_id,
                source="career_page",
                raw_data={
                    "found_leads": [
                        {
                            "email": "careers@stjude.org",
                            "name": "Clay Mcleod",
                            "company": "St. Jude Children's Research Hospital",
                            "job_title": "Bioinformatics Engineer",
                            "job_url": "https://www.stjude.org/jobs",
                            "platform": "career_page"
                        }
                    ]
                },
                status="pending"
            )
            db.add(q_item)
            await db.commit()
            
            print("Normalize running...")
            count = await normalize_scrape_queue(user_id, db)
            print(f"Normalized count: {count}")
            
            # Fetch contact and verify if email got processed
            c_res = await db.execute(select(Contact).where(Contact.user_id == user_id))
            contacts = c_res.scalars().all()
            assert len(contacts) == 1
            c = contacts[0]
            print(f"Contact Name: {c.name}, Email: {c.email}, Role: {c.role}, Company: {c.company}")
            
            # Verify contact was saved properly
            assert c.name == "Clay Mcleod"
            assert "@" in c.email
            
            # Clean up
            from sqlalchemy import delete
            from app.models import Template
            await db.execute(delete(Contact).where(Contact.user_id == user_id))
            await db.execute(delete(ScrapeQueue).where(ScrapeQueue.user_id == user_id))
            await db.execute(delete(Setting).where(Setting.user_id == user_id))
            await db.execute(delete(Template).where(Template.user_id == user_id))
            await db.execute(delete(User).where(User.id == user_id))
            await db.commit()
            
        print("Automatic Apollo enrichment test compiled and completed successfully!")

if __name__ == '__main__':
    asyncio.run(main())
