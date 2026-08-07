import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import engine, Base, AsyncSessionLocal
from app.models import Contact

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Sign up or login
        res = await client.post("/auth/signup", json={"email": "metrics_test@example.com", "password": "Password123!"})
        if res.status_code == 201:
            token = res.json()["access_token"]
        else:
            res = await client.post("/auth/login", json={"email": "metrics_test@example.com", "password": "Password123!"})
            token = res.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a generic contact
        await client.post("/contacts", headers=headers, json={
            "name": "Hiring Manager",
            "company": "Google",
            "role": "SDE",
            "source": "linkedin_jobs",
            "email": "careers@google.com"
        })
        
        # Create a named contact
        await client.post("/contacts", headers=headers, json={
            "name": "Sundar Pichai",
            "company": "Google",
            "role": "CEO",
            "source": "linkedin_jobs",
            "email": "sundar@google.com"
        })
        
        # Call metrics endpoint
        m_res = await client.get("/contacts/metrics", headers=headers)
        assert m_res.status_code == 200
        metrics = m_res.json()
        print("Metrics Output:", metrics)
        
        # Check expected counts
        assert len(metrics) > 0
        match = next(x for x in metrics if x["source"] == "linkedin_jobs")
        assert match["leads_found"] == 2
        assert match["real_name_count"] == 1
        assert match["generic_count"] == 1
        
        # Clean up contacts from DB for this user
        async with AsyncSessionLocal() as db:
            from sqlalchemy import delete
            from app.models import User
            # find user
            from sqlalchemy import select
            user_res = await db.execute(select(User).where(User.email == "metrics_test@example.com"))
            user = user_res.scalar_one_or_none()
            if user:
                await db.execute(delete(Contact).where(Contact.user_id == user.id))
                await db.execute(delete(User).where(User.id == user.id))
                await db.commit()
        print("Cleanup done! Test passed successfully.")

if __name__ == '__main__':
    asyncio.run(main())
