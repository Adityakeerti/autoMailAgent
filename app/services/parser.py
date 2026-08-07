import io
import json
import logging
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models import Resume, ContextProfile, ContextExperience, ContextProject, ContextAchievement
from app.services.storage import storage_service
from app.services.llm import llm_service

logger = logging.getLogger("resume_parser")

EXTRACTION_SYSTEM_PROMPT = """
You are an expert HR & resume parser. Your task is to extract complete, high-depth context information from the provided resume text into a strict JSON format matching this exact schema:

{
  "profile": {
    "role_title": "string or null",
    "full_name": "string or null",
    "grad_year": "string or null",
    "portfolio_url": "string or null",
    "github_url": "string or null",
    "email": "string or null"
  },
  "experience": [
    {
      "title": "string (Company / Role)",
      "dates": "string or null",
      "one_liner": "Detailed description containing all bullet points, technical achievements, architecture, and impact from the resume without oversimplifying.",
      "stack": ["skill1", "skill2"],
      "tags": ["backend", "python", "fastapi"]
    }
  ],
  "projects": [
    {
      "title": "string",
      "dates": "string or null",
      "one_liner": "Complete detailed description capturing all features, architecture, tools, frameworks, and metrics from the resume. Do NOT oversimplify or cut depth.",
      "stack": ["skill1", "skill2"],
      "tags": ["react", "frontend", "aws"],
      "link": "url or null",
      "live_link": "url or null",
      "note": "string or null"
    }
  ],
  "achievements": [
    {
      "text": "Full detailed achievement text"
    }
  ]
}

Strict Rules:
- Return ONLY valid JSON, no markdown code block wrappers or conversational text.
- Preserve full technical depth, bullet points, metrics, and features for projects & experiences. Do NOT reduce a 3-bullet project into a 5-word sentence.
- Do NOT invent false claims or superlatives not present in the resume.
"""

def extract_text_from_file_bytes(file_bytes: bytes, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            text_parts = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(text_parts)
        except Exception as e:
            logger.warning(f"PdfReader failed: {e}")
    
    try:
        return file_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return ""

async def parse_and_populate_resume(resume_id: int, db: AsyncSession, mode: str = "keep_unique"):
    """
    Parse resume and populate user context layer preserving complete technical depth.
    :param mode: 'replace' (remove old info and replace) OR 'keep_unique' (keep existing and append unique items)
    """
    res = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = res.scalar_one_or_none()
    if not resume:
        return

    try:
        file_bytes = storage_service.get_resume_bytes(resume.file_url)
        raw_text = extract_text_from_file_bytes(file_bytes, resume.file_name or "resume.pdf")

        if not raw_text.strip():
            resume.parsed_status = "failed"
            await db.commit()
            return

        user_prompt = f"Resume text:\n{raw_text[:6000]}"
        llm_response = await llm_service.generate_text(
            prompt=user_prompt,
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            high_tier=True,
            json_mode=True
        )

        json_str = llm_response.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        data = json.loads(json_str)
        user_id = resume.user_id

        if mode == "replace":
            await db.execute(delete(ContextExperience).where(ContextExperience.user_id == user_id))
            await db.execute(delete(ContextProject).where(ContextProject.user_id == user_id))
            await db.execute(delete(ContextAchievement).where(ContextAchievement.user_id == user_id))
            await db.commit()

        # Update profile
        prof_data = data.get("profile", {})
        res_prof = await db.execute(select(ContextProfile).where(ContextProfile.user_id == user_id))
        cp = res_prof.scalar_one_or_none()
        if not cp:
            cp = ContextProfile(user_id=user_id)
            db.add(cp)
        
        if prof_data.get("role_title"): cp.role_title = prof_data.get("role_title")
        if prof_data.get("full_name"): cp.full_name = prof_data.get("full_name")
        if prof_data.get("grad_year"): cp.grad_year = str(prof_data.get("grad_year"))
        if prof_data.get("portfolio_url"): cp.portfolio_url = prof_data.get("portfolio_url")
        if prof_data.get("github_url"): cp.github_url = prof_data.get("github_url")
        if prof_data.get("email"): cp.email = prof_data.get("email")

        existing_exp_titles = set()
        existing_proj_titles = set()
        existing_ach_texts = set()

        if mode == "keep_unique":
            res_e = await db.execute(select(ContextExperience.title).where(ContextExperience.user_id == user_id))
            existing_exp_titles = set(t.lower() for (t,) in res_e.all())

            res_p = await db.execute(select(ContextProject.title).where(ContextProject.user_id == user_id))
            existing_proj_titles = set(t.lower() for (t,) in res_p.all())

            res_a = await db.execute(select(ContextAchievement.text).where(ContextAchievement.user_id == user_id))
            existing_ach_texts = set(t.lower() for (t,) in res_a.all())

        # Experience
        exp_list = data.get("experience", [])
        for item in exp_list:
            title = item.get("title", "Experience")
            if mode == "keep_unique" and title.lower() in existing_exp_titles:
                continue
            db.add(ContextExperience(
                user_id=user_id,
                title=title,
                dates=item.get("dates"),
                one_liner=item.get("one_liner"),
                stack=item.get("stack", []),
                tags=item.get("tags", [])
            ))

        # Projects
        proj_list = data.get("projects", [])
        for item in proj_list:
            title = item.get("title", "Project")
            if mode == "keep_unique" and title.lower() in existing_proj_titles:
                continue
            db.add(ContextProject(
                user_id=user_id,
                title=title,
                dates=item.get("dates"),
                one_liner=item.get("one_liner"),
                stack=item.get("stack", []),
                tags=item.get("tags", []),
                link=item.get("link"),
                live_link=item.get("live_link"),
                note=item.get("note")
            ))

        # Achievements
        ach_list = data.get("achievements", [])
        for item in ach_list:
            text = item.get("text") if isinstance(item, dict) else str(item)
            if mode == "keep_unique" and text.lower() in existing_ach_texts:
                continue
            db.add(ContextAchievement(
                user_id=user_id,
                text=text
            ))

        resume.parsed_status = "done"
        await db.commit()

    except Exception as e:
        logger.error(f"Error parsing resume {resume_id}: {e}")
        resume.parsed_status = "failed"
        await db.commit()
