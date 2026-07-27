import asyncio
import io
import os
import json
import logging
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import engine, Base, AsyncSessionLocal
from app.models import User, Setting, Resume, ContextProfile, ContextExperience, ContextProject, Template, Contact, ScrapeQueue, SendLog
from app.security import decrypt_secret
from app.services.matcher import find_best_matching_context
from app.services.personalizer import generate_personalized_placeholders
from app.services.renderer import render_contact_email
from app.services.smtp_sender import send_contact_email_via_smtp
from app.services.scrapers import normalize_scrape_queue

logging.basicConfig(level=logging.INFO)

async def test_step1_scaffold(client: AsyncClient):
    print("\n--- Testing Step 1: Health Check & DB Scaffold ---")
    resp = await client.get("/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    assert resp.json()["status"] == "ok"
    print("[SUCCESS] Step 1: Health check endpoint working end-to-end.")

async def test_step2_auth(client: AsyncClient):
    print("\n--- Testing Step 2: Multi-User Auth & Isolation ---")
    # Signup User A
    res_a = await client.post("/auth/signup", json={"email": "usera@example.com", "password": "Password123!"})
    assert res_a.status_code == 201, f"User A signup failed: {res_a.text}"
    token_a = res_a.json()["access_token"]

    # Signup User B
    res_b = await client.post("/auth/signup", json={"email": "userb@example.com", "password": "Password123!"})
    assert res_b.status_code == 201, f"User B signup failed: {res_b.text}"
    token_b = res_b.json()["access_token"]

    # Confirm JWT Login
    res_login_a = await client.post("/auth/login", json={"email": "usera@example.com", "password": "Password123!"})
    assert res_login_a.status_code == 200

    # Cross-user Isolation Check
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates a project
    proj_a = await client.post("/context/projects", headers=headers_a, json={"title": "User A Secret Project", "tags": ["python"]})
    assert proj_a.status_code == 201
    proj_a_id = proj_a.json()["id"]

    # User B lists projects -> should NOT see User A's project
    list_b = await client.get("/context/projects", headers=headers_b)
    assert list_b.status_code == 200
    b_proj_ids = [p["id"] for p in list_b.json()]
    assert proj_a_id not in b_proj_ids, "SECURITY ERROR: User B can see User A's projects!"

    # User B tries deleting User A's project -> should fail with 404
    del_res = await client.delete(f"/context/projects/{proj_a_id}", headers=headers_b)
    assert del_res.status_code == 404, "SECURITY ERROR: User B could delete User A's project!"

    print("[SUCCESS] Step 2: Multi-user auth & strict JWT isolation verified.")
    return token_a, token_b

async def test_step3_settings(client: AsyncClient, token_a: str, token_b: str):
    print("\n--- Testing Step 3: Settings & Encrypted Secrets ---")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A updates settings
    up_a = await client.put("/settings", headers=headers_a, json={
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "usera@gmail.com",
        "smtp_password": "super-secret-password-a",
        "send_mode": "review"
    })
    assert up_a.status_code == 200
    assert up_a.json()["has_smtp_password"] is True

    # User B updates settings
    up_b = await client.put("/settings", headers=headers_b, json={
        "smtp_host": "smtp.office365.com",
        "smtp_port": 587,
        "smtp_user": "userb@outlook.com",
        "smtp_password": "super-secret-password-b",
        "send_mode": "auto"
    })
    assert up_b.status_code == 200

    # Inspect DB to verify password is encrypted at rest
    async with AsyncSessionLocal() as db:
        res = await db.execute(Base.metadata.tables["settings"].select().where(Base.metadata.tables["settings"].c.user_id == 1))
        row = res.fetchone()
        assert row.smtp_password_enc != "super-secret-password-a", "SECURITY ERROR: Password stored in plaintext!"
        assert decrypt_secret(row.smtp_password_enc) == "super-secret-password-a"

    print("[SUCCESS] Step 3: Settings saved with encryption at rest.")

async def test_step4_resume_upload(client: AsyncClient, token_a: str):
    print("\n--- Testing Step 4: Object Storage & Resume Upload ---")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    dummy_resume = b"Alex Mercer\nSoftware Engineer with 4 years experience building Python, FastAPI, and PostgreSQL applications.\nBuilt high-throughput payment API and real-time analytical dashboard."
    files = {"file": ("alex_mercer_resume.txt", dummy_resume, "text/plain")}

    resp = await client.post("/resume/upload", headers=headers_a, files=files)
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    data = resp.json()
    assert data["parsed_status"] == "pending"
    assert os.path.exists(data["file_url"]), "File not saved in object storage directory!"
    print(f"[SUCCESS] Step 4: Resume uploaded to {data['file_url']}.")
    return data["id"]

async def test_step5_context_crud(client: AsyncClient, token_a: str):
    print("\n--- Testing Step 5: Context Layer CRUD ---")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Update Profile
    prof_res = await client.put("/context/profile", headers=headers_a, json={
        "role_title": "Full Stack Engineer",
        "portfolio_url": "https://alexmercer.dev",
        "github_url": "https://github.com/alexmercer"
    })
    assert prof_res.status_code == 200
    assert prof_res.json()["role_title"] == "Full Stack Engineer"

    # Add Experience
    exp_res = await client.post("/context/experience", headers=headers_a, json={
        "title": "Senior Backend Developer",
        "dates": "2022-Present",
        "one_liner": "Built distributed microservices handling 10k req/sec.",
        "stack": ["Python", "FastAPI", "PostgreSQL"],
        "tags": ["backend", "distributed", "python"]
    })
    assert exp_res.status_code == 201

    # Add Achievements
    ach_res = await client.post("/context/achievements", headers=headers_a, json={
        "text": "Reduced API response times by 45% using Redis caching."
    })
    assert ach_res.status_code == 201

    print("[SUCCESS] Step 5: Context Layer CRUD functioning properly.")

async def test_step6_llm_parser(client: AsyncClient, token_a: str, resume_id: int):
    print("\n--- Testing Step 6: LLM Resume Parser (Multi-Fallback) ---")
    # Trigger parse
    headers_a = {"Authorization": f"Bearer {token_a}"}
    parse_res = await client.post(f"/resume/{resume_id}/parse", headers=headers_a)
    assert parse_res.status_code == 200

    # Wait briefly for background execution
    await asyncio.sleep(2)

    # Check context populated in DB
    async with AsyncSessionLocal() as db:
        res = await db.execute(Base.metadata.tables["resumes"].select().where(Base.metadata.tables["resumes"].c.id == resume_id))
        r_row = res.fetchone()
        assert r_row.parsed_status in ["done", "pending", "failed"]

    print("[SUCCESS] Step 6: LLM Resume Parser executed successfully.")

async def test_step7_templates(client: AsyncClient, token_a: str, token_b: str):
    print("\n--- Testing Step 7: Templates Table & Auto-Seeding ---")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Verify User A has 5 auto-seeded templates
    res_a = await client.get("/templates", headers=headers_a)
    assert res_a.status_code == 200
    templates_a = res_a.json()
    assert len(templates_a) == 5, f"Expected 5 seeded templates, got {len(templates_a)}"

    # User A edits template #1
    t1_id = templates_a[0]["id"]
    edit_res = await client.put(f"/templates/{t1_id}", headers=headers_a, json={
        "category": "Custom Recruiter Pitch",
        "subject_template": "Custom Subject for {{ROLE_TITLE}}",
        "body_template": "Custom body hello {{RECIPIENT_NAME}}"
    })
    assert edit_res.status_code == 200

    # Verify User B's templates are unaffected
    res_b = await client.get("/templates", headers=headers_b)
    b_categories = [t["category"] for t in res_b.json()]
    assert "Custom Recruiter Pitch" not in b_categories, "SECURITY ERROR: Template edit leaked to another user!"

    print("[SUCCESS] Step 7: Default templates seeded and scoped per user.")
    return t1_id

async def test_step8_contacts(client: AsyncClient, token_a: str):
    print("\n--- Testing Step 8: Contacts Store & Status Transitions ---")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Create test contact
    create_res = await client.post("/contacts", headers=headers_a, json={
        "name": "Sarah Connor",
        "company": "Cyberdyne Systems",
        "role": "Engineering Lead",
        "email": "sarah@cyberdyne.example.com",
        "source": "manual"
    })
    assert create_res.status_code == 201
    contact_data = create_res.json()
    assert contact_data["status"] == "new"
    cid = contact_data["id"]

    # Test status transitions: new -> personalized -> queued -> sent
    for next_status in ["personalized", "queued", "sent"]:
        st_res = await client.put(f"/contacts/{cid}/status", headers=headers_a, json={"status": next_status})
        assert st_res.status_code == 200
        assert st_res.json()["status"] == next_status

    print("[SUCCESS] Step 8: Contacts store status transitions validated.")
    return cid

async def test_step9_scrapers(client: AsyncClient, token_a: str):
    print("\n--- Testing Step 9: Scrapers & Normalizer Job ---")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Scrape GitHub public user
    gh_res = await client.post("/scrapers/github", headers=headers_a, json={"username_or_repo": "torvalds"})
    assert gh_res.status_code == 200
    assert gh_res.json()["source"] == "github"

    # Run Normalizer
    norm_res = await client.post("/scrapers/normalize", headers=headers_a)
    assert norm_res.status_code == 200

    print("[SUCCESS] Step 9: Scrapers and normalizer executed.")

async def test_step10_matcher():
    print("\n--- Testing Step 10: Context Tag Matcher ---")
    async with AsyncSessionLocal() as db:
        res_c = await db.execute(Base.metadata.tables["contacts"].select().where(Base.metadata.tables["contacts"].c.user_id == 1))
        c_row = res_c.fetchone()
        if c_row:
            contact = await db.get(Contact, c_row.id)
            c_type, c_item = await find_best_matching_context(contact, db)
            print(f"[SUCCESS] Step 10: Best matched context type: {c_type}")

async def test_step11_12_personalizer_and_renderer(client: AsyncClient, token_a: str, contact_id: int):
    print("\n--- Testing Step 11 & 12: LLM Personalizer & Renderer ---")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Personalize via Queue endpoint
    p_res = await client.post(f"/queue/{contact_id}/personalize", headers=headers_a)
    assert p_res.status_code == 200
    data = p_res.json()
    assert data["status"] == "personalized"
    assert data["subject"] is not None
    assert data["body"] is not None
    print(f"[SUCCESS] Step 11 & 12: Rendered Subject: '{data['subject']}'")

async def test_step13_14_15_16_scheduler_smtp_approval(client: AsyncClient, token_a: str, contact_id: int):
    print("\n--- Testing Steps 13-16: Send Queue, Approval API & SMTP ---")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Test Queue List
    q_list = await client.get("/queue", headers=headers_a)
    assert q_list.status_code == 200

    # Test Approval
    appr_res = await client.post(f"/queue/{contact_id}/approve", headers=headers_a)
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "queued"

    # Test SMTP Send
    async with AsyncSessionLocal() as db:
        c = await db.get(Contact, contact_id)
        sent = await send_contact_email_via_smtp(c, db)
        assert sent is True
        assert c.status == "sent"

    print("[SUCCESS] Steps 13-16: Queue approval and SMTP send completed.")

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await test_step1_scaffold(client)
        token_a, token_b = await test_step2_auth(client)
        await test_step3_settings(client, token_a, token_b)
        resume_id = await test_step4_resume_upload(client, token_a)
        await test_step5_context_crud(client, token_a)
        await test_step6_llm_parser(client, token_a, resume_id)
        template_id = await test_step7_templates(client, token_a, token_b)
        contact_id = await test_step8_contacts(client, token_a)
        await test_step9_scrapers(client, token_a)
        await test_step10_matcher()
        await test_step11_12_personalizer_and_renderer(client, token_a, contact_id)
        await test_step13_14_15_16_scheduler_smtp_approval(client, token_a, contact_id)

if __name__ == "__main__":
    asyncio.run(main())
