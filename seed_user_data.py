import asyncio
import sys
from sqlalchemy import select

from app.database import AsyncSessionLocal, init_db
from app.models import User, Setting, Template, ContextProfile, ContextExperience, ContextProject, ContextAchievement
from app.security import hash_password
from app.services.default_templates import DEFAULT_TEMPLATES

SEED_DATA = {
  "profile": {
    "role_title": "Final-year B.Tech CSE (AI/ML) student, Graphic Era Hill University",
    "grad_year": "2027",
    "portfolio_url": "https://adityakeerti.vercel.app",
    "github_url": "https://github.com/Adityakeerti",
    "email": "adityacodes404@gmail.com"
  },
  "experience": [
    {
      "title": "Software Engineering Intern, Peerprep",
      "dates": "Mar 2026 - May 2026",
      "one_liner": "Built an automated ingestion engine in Python that standardizes and extracts data from unpredictable, multi-format academic documents, cutting per-record processing time from 10 minutes to ~30 seconds at 99.98% validation accuracy.",
      "stack": ["Python", "OpenCV", "OCR", "Git"],
      "tags": ["backend", "python", "data-pipeline", "ocr", "internship"]
    }
  ],
  "projects": [
    {
      "title": "R.A.G.E. — Windows Automation Agent",
      "dates": "May 2026 - Present",
      "one_liner": "Built a Windows agent that executes multi-step goals via an adaptive ReAct feedback loop, observing window state and self-correcting on errors, backed by an SQLite rollback ledger and regex-based safety filters.",
      "stack": ["Python", "TypeScript", "React", "SQLite", "Win32 API", "pywebview", "CustomTkinter"],
      "tags": ["ai-agent", "llm", "python", "react", "automation", "desktop"],
      "link": "https://github.com/Adityakeerti/desktop-ai-agent"
    },
    {
      "title": "DOC-OC — Automated Marksheet Extraction",
      "dates": "Sep 2025 - Oct 2025",
      "one_liner": "Built a multi-board marksheet extraction pipeline (YOLOv8, OpenCV, Table Transformers) with a custom structure-retaining OCR engine and fraud-mitigation checks, driving a 30x reduction in processing time.",
      "stack": ["Python", "TypeScript", "React", "FastAPI", "YOLOv8", "HuggingFace", "OpenCV", "MySQL"],
      "tags": ["ml", "computer-vision", "python", "fastapi", "data-pipeline"],
      "live_link": "adityacodes404-doc-oc.hf.space"
    },
    {
      "title": "Advanzia AutoLend — Autonomous Credit Limit Optimization",
      "dates": "Jan 2026 - Feb 2026",
      "one_liner": "Built a Dueling Double DQN risk-optimization engine combined with a Cox Proportional Hazard model, on a Spring Boot + FastAPI microservices backend benchmarked at 5,000+ req/min with sub-300ms inference latency.",
      "stack": ["Java", "Spring Boot", "Python", "FastAPI", "PyTorch", "Redis", "PostgreSQL"],
      "tags": ["ml", "reinforcement-learning", "backend", "java", "python", "microservices"],
      "live_link": "autocreditrl.vercel.app",
      "note": "Finalist project, HackTheWinter National Hackathon"
    },
    {
      "title": "LivAna",
      "one_liner": "Built a PG/mess/grocery platform for students with a 14-table BCNF schema, 58 REST endpoints, and JWT auth, as team lead.",
      "stack": ["Spring Boot", "PostgreSQL", "REST API", "JWT"],
      "tags": ["backend", "java", "spring-boot", "postgres", "system-design", "team-lead"]
    },
    {
      "title": "Quick-Commerce Backend Audit",
      "one_liner": "Ran a deep debugging audit on a Spring Boot quick-commerce backend and found a hardcoded auth bypass and an unprotected refund endpoint.",
      "stack": ["Spring Boot", "Redis", "React Native", "Next.js"],
      "tags": ["backend", "security", "debugging", "java", "spring-boot"]
    },
    {
      "title": "Redrob AI Candidate Ranker",
      "one_liner": "Built a hybrid multi-stage candidate ranking pipeline (bi-encoder retrieval, BM25, NLI logic gates, cross-encoder reranking) with a Streamlit demo, at a hackathon.",
      "stack": ["Python", "Sentence Transformers", "BM25", "NLI", "Streamlit"],
      "tags": ["ml", "nlp", "search", "ranking", "python", "hackathon"]
    }
  ],
  "achievements": [
    "1st Place, MariTHON National Hackathon — SOF extraction pipeline on Google Cloud Vertex AI for the Integrated Maritime Exchange",
    "Finalist, HackTheWinter National Hackathon",
    "Finalist, India Innovates 2026 — Top 500 teams, physical finale at Bharat Mandapam, New Delhi"
  ]
}

async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        email = SEED_DATA["profile"]["email"]
        
        # Check if user exists
        res = await db.execute(select(User).where(User.email == email))
        user = res.scalar_one_or_none()
        
        if not user:
            print(f"Creating user {email}...")
            user = User(
                email=email,
                password_hash=hash_password("Password123!")
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

            # Settings
            db.add(Setting(user_id=user.id))
            
            # Default templates
            for tmpl in DEFAULT_TEMPLATES:
                db.add(Template(
                    user_id=user.id,
                    category=tmpl["category"],
                    subject_template=tmpl["subject_template"],
                    body_template=tmpl["body_template"]
                ))
            await db.commit()

        user_id = user.id

        # Seed Profile
        prof = SEED_DATA["profile"]
        res_p = await db.execute(select(ContextProfile).where(ContextProfile.user_id == user_id))
        cp = res_p.scalar_one_or_none()
        if not cp:
            cp = ContextProfile(user_id=user_id)
            db.add(cp)
        
        cp.role_title = prof["role_title"]
        cp.grad_year = str(prof["grad_year"])
        cp.portfolio_url = prof["portfolio_url"]
        cp.github_url = prof["github_url"]
        cp.email = prof["email"]

        # Seed Experience
        for exp in SEED_DATA["experience"]:
            db.add(ContextExperience(
                user_id=user_id,
                title=exp["title"],
                dates=exp.get("dates"),
                one_liner=exp.get("one_liner"),
                stack=exp.get("stack", []),
                tags=exp.get("tags", [])
            ))

        # Seed Projects
        for proj in SEED_DATA["projects"]:
            db.add(ContextProject(
                user_id=user_id,
                title=proj["title"],
                dates=proj.get("dates"),
                one_liner=proj.get("one_liner"),
                stack=proj.get("stack", []),
                tags=proj.get("tags", []),
                link=proj.get("link"),
                live_link=proj.get("live_link"),
                note=proj.get("note")
            ))

        # Seed Achievements
        for ach in SEED_DATA["achievements"]:
            db.add(ContextAchievement(
                user_id=user_id,
                text=ach
            ))

        await db.commit()
        print(f"Successfully seeded data for {email} (User ID: {user_id})!")

if __name__ == "__main__":
    asyncio.run(seed())
