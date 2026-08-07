import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_automail.db"

import asyncio
import random
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch
from app.main import app
from app.database import engine, Base, AsyncSessionLocal
from app.models import Contact, ScrapeQueue, Setting, User, Template
from app.services.scrapers import normalize_scrape_queue, scraper_service
from app.services.renderer import render_contact_email
from app.workers.scheduler import process_user_queue

async def mock_find_tech_lead(domain: str):
    return {
        "email": "john.techlead@mitremedia.com",
        "name": "John TechLead",
        "job_title": "Lead Software Engineer",
        "company": "Mitremedia",
        "linkedin_url": "https://linkedin.com/in/johntechlead",
        "platform": "apollo"
    }

async def main():
    # Clean and initialize test database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    email_suffix = str(random.randint(1000, 9999))
    test_email = f"step35_test_{email_suffix}@example.com"
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Sign up user
        res = await client.post("/auth/signup", json={"email": test_email, "password": "Password123!"})
        assert res.status_code == 201, f"Signup failed: {res.text}"
        token = res.json()["access_token"]
        
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            user_res = await db.execute(select(User).where(User.email == test_email))
            user = user_res.scalar_one_or_none()
            user_id = user.id
            
            # Make sure settings has APOLLO_API_KEY
            from app.config import settings
            old_key = settings.APOLLO_API_KEY
            settings.APOLLO_API_KEY = "test-mock-apollo-key"
            
            # Update setting send_mode to auto and expand schedule window to 24 hours
            res_s = await db.execute(select(Setting).where(Setting.user_id == user_id))
            st = res_s.scalar_one_or_none()
            st.send_mode = "auto"
            st.schedule_window = "00:00-23:59"
            await db.commit()

            # Add a generic lead in the Scrape Queue
            q_item = ScrapeQueue(
                user_id=user_id,
                source="auto_discover",
                raw_data={
                    "found_leads": [
                        {
                            "email": "careers@mitremedia.com",
                            "company": "Mitremedia",
                            "job_title": "Software Engineer",
                            "job_url": "https://mitremedia.com/careers/swe",
                            "platform": "auto_discover"
                        }
                    ]
                },
                status="pending"
            )
            db.add(q_item)
            await db.commit()
            
            # 2. Test Apollo tech lead discovery & enrichment during normalization
            print("Running normalize_scrape_queue...")
            with patch.object(scraper_service, "find_and_enrich_tech_lead", mock_find_tech_lead):
                count = await normalize_scrape_queue(user_id, db)
            assert count == 1, "Should have normalized 1 contact"
            
            # Fetch contact and verify it was enriched with the Tech Lead's details
            c_res = await db.execute(select(Contact).where(Contact.user_id == user_id))
            contacts = c_res.scalars().all()
            assert len(contacts) == 1
            c = contacts[0]
            print(f"Normalized Contact Details -> Name: {c.name}, Email: {c.email}, Role: {c.role}, Company: {c.company}, Status: {c.status}")
            
            assert c.name == "John TechLead"
            assert c.email == "john.techlead@mitremedia.com"
            assert c.role == "Lead Software Engineer"
            assert c.company == "Mitremedia"
            # Since it was enriched to a real named contact, it should have status "new" (not "generic_new")
            assert c.status == "new"

            # 3. Test Template Selection
            # Clear seeded templates first to use our custom ones
            from sqlalchemy import delete
            await db.execute(delete(Template).where(Template.user_id == user_id))
            await db.commit()
            
            # Create default templates for the user
            templates = [
                Template(
                    user_id=user_id,
                    category="Referral Ask",
                    subject_template="Referral Request: {{ROLE_TITLE}} at {{COMPANY}}",
                    body_template="Hi {{RECIPIENT_NAME}}, I am looking for a referral for {{ROLE_TITLE}} at {{COMPANY}}. Best, {{USER_NAME}}"
                ),
                Template(
                    user_id=user_id,
                    category="Direct Tech Lead Pitch",
                    subject_template="Pitch: {{ROLE_TITLE}} at {{COMPANY}}",
                    body_template="Hi {{RECIPIENT_NAME}}, here is my pitch for {{ROLE_TITLE}} at {{COMPANY}}. Best, {{USER_NAME}}"
                )
            ]
            db.add_all(templates)
            await db.commit()

            # Case A: Contact is hiring (job_posting_url is set). Should choose "Referral Ask".
            assert c.job_posting_url == "https://mitremedia.com/careers/swe"
            c = await render_contact_email(c.id, None, db)
            print(f"Case A (Hiring) Template Subject: '{c.subject}'")
            assert "Referral Request" in c.subject, f"Expected Referral Ask template, got '{c.subject}'"

            # Case B: Contact is not hiring (job_posting_url is empty). Should choose "Direct Tech Lead Pitch".
            c.job_posting_url = ""
            c.subject = None
            c.body = None
            c.status = "new"
            await db.commit()
            c = await render_contact_email(c.id, None, db)
            print(f"Case B (Not Hiring) Template Subject: '{c.subject}'")
            assert "Pitch" in c.subject, f"Expected Direct Tech Lead Pitch template, got '{c.subject}'"

            # 4. Test Auto-Personalization in Scheduler
            c.status = "new"
            c.subject = None
            c.body = None
            await db.commit()
            
            with patch("app.workers.scheduler.send_contact_email_via_smtp") as mock_send:
                mock_send.return_value = True
                
                print("Running scheduler process_user_queue...")
                await process_user_queue(user_id)
                
                # Verify contact was auto-personalized and queued
                await db.refresh(c)
                print(f"After Scheduler Tick -> Contact Status: {c.status}, Subject: {c.subject}")
                assert c.status == "sent", f"Expected contact status to be sent (auto-personalized -> queued -> sent), got {c.status}"
                assert c.subject is not None
                assert c.body is not None

            # Clean up user and data
            from sqlalchemy import delete
            await db.execute(delete(Contact).where(Contact.user_id == user_id))
            await db.execute(delete(ScrapeQueue).where(ScrapeQueue.user_id == user_id))
            await db.execute(delete(Setting).where(Setting.user_id == user_id))
            await db.execute(delete(Template).where(Template.user_id == user_id))
            await db.execute(delete(User).where(User.id == user_id))
            await db.commit()

            # Restore APOLLO_API_KEY
            settings.APOLLO_API_KEY = old_key

        print("\nSmart Tech Lead Enrichment & Role-Aware Selection tests passed successfully!")

if __name__ == '__main__':
    asyncio.run(main())
