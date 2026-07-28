import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import AsyncSessionLocal
from app.models import Contact, Template

async def main():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Sign up or login
        res = await client.post("/auth/signup", json={"email": "generic_test@example.com", "password": "Password123!"})
        if res.status_code == 201:
            token = res.json()["access_token"]
        else:
            res = await client.post("/auth/login", json={"email": "generic_test@example.com", "password": "Password123!"})
            token = res.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Verify the user has the Generic Company Outreach template seeded
        t_res = await client.get("/templates", headers=headers)
        assert t_res.status_code == 200
        templates = t_res.json()
        categories = [t["category"] for t in templates]
        print("Categories:", categories)
        assert "Generic Company Outreach" in categories
        
        # Create a contact with status generic_new (synthesized lead type)
        # Note: in normalize_scrape_queue this gets mapped to generic_new
        # We can test creating it directly as new but with name/email that triggers is_synthesized,
        # or we can test the rendering logic by manually setting status to generic_new.
        # Let's create a contact
        c_res = await client.post("/contacts", headers=headers, json={
            "name": "Hiring Manager",
            "company": "Stripe",
            "role": "Backend Engineer",
            "source": "auto_discover",
            "email": "careers@stripe.com"
        })
        assert c_res.status_code == 201
        contact_id = c_res.json()["id"]
        
        # Manually update status to generic_new (to simulate normalize_scrape_queue behavior)
        up_res = await client.put(f"/contacts/{contact_id}/status", headers=headers, json={"status": "generic_new"})
        assert up_res.status_code == 200
        assert up_res.json()["status"] == "generic_new"
        
        # Approve it: should resolve to generic_queued and render plain template
        app_res = await client.post(f"/queue/{contact_id}/approve", headers=headers)
        assert app_res.status_code == 200
        updated = app_res.json()
        assert updated["status"] == "generic_queued"
        assert "Engineering opportunities at Stripe" in updated["subject"]
        assert "I noticed Stripe is hiring for a Backend Engineer position." in updated["body"]
        assert updated["personalized_data"] == {} # Should have bypassed LLM Personalization!
        print("Subject Rendered:", updated["subject"])
        print("Body Rendered Preview:", updated["body"][:150])
        
        # Clean up database
        async with AsyncSessionLocal() as db:
            from sqlalchemy import delete
            from app.models import User
            from sqlalchemy import select
            user_res = await db.execute(select(User).where(User.email == "generic_test@example.com"))
            user = user_res.scalar_one_or_none()
            if user:
                await db.execute(delete(Contact).where(Contact.user_id == user.id))
                await db.execute(delete(Template).where(Template.user_id == user.id))
                await db.execute(delete(User).where(User.id == user.id))
                await db.commit()
                
        print("Generic queue test passed successfully!")

if __name__ == '__main__':
    asyncio.run(main())
