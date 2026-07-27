import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Contact, Template, ContextProject, ContextExperience, SendLog
from app.services.llm import llm_service
from app.services.matcher import find_best_matching_context

logger = logging.getLogger("personalizer")

PERSONALIZER_SYSTEM_PROMPT = """
You are an expert cold email copywriter. Generate tailored placeholders for a job application cold email.

Strict Tone & Style Rules:
- Tone: Professional, direct, plain statement of facts and technical problem solved.
- Absolute Prohibition: NO superlatives (e.g., "amazing", "revolutionary", "proud to share", "thrilled to connect").
- Length: Concise. The final text must keep the overall email under ~120 words total.
- Hook phrasing: Must be unique and relevant to the company or recipient's domain.

Return a JSON object with these exact keys:
{
  "PERSONAL_HOOK": "One short sentence connecting to recipient/company domain.",
  "RELEVANT_PROJECT_LINE": "1-2 sentences describing what project/experience was built and technical problem solved plain and clear.",
  "WHY_THIS_COMPANY": "One short sentence why their technology or mission is relevant."
}
"""

async def generate_personalized_placeholders(
    contact: Contact,
    template: Template,
    db: AsyncSession
) -> Dict[str, str]:

    context_type, context_item = await find_best_matching_context(contact, db)

    # Get recent hooks for this user to avoid repeating phrasing
    recent_logs = await db.execute(
        select(Contact.personalized_data)
        .where(Contact.user_id == contact.user_id, Contact.status.in_(["queued", "sent"]))
        .order_by(Contact.id.desc())
        .limit(5)
    )
    recent_hooks = []
    for (p_data,) in recent_logs.all():
        if isinstance(p_data, dict) and p_data.get("PERSONAL_HOOK"):
            recent_hooks.append(p_data.get("PERSONAL_HOOK"))

    avoid_clause = f" Avoid repeating these recent hooks: {recent_hooks}" if recent_hooks else ""

    context_desc = ""
    if context_item:
        if context_type == "project":
            context_desc = f"Project: {context_item.title}. Summary: {context_item.one_liner}. Stack: {context_item.stack}."
        else:
            context_desc = f"Experience: {context_item.title}. Summary: {context_item.one_liner}. Stack: {context_item.stack}."

    user_prompt = f"""
Target Recipient: {contact.name or 'Hiring Manager'}
Target Company: {contact.company or 'Target Company'}
Target Role: {contact.role or 'Software Engineer'}
Source/Job Link: {contact.job_posting_url or 'N/A'}

Matched User Context:
{context_desc or 'General Software Engineering experience building web applications and backend systems.'}
{avoid_clause}
"""

    try:
        # Use high_tier=False for med-high level LLMs on small tasks (hook lines, project lines)
        response_text = await llm_service.generate_text(
            prompt=user_prompt,
            system_prompt=PERSONALIZER_SYSTEM_PROMPT,
            high_tier=False,
            json_mode=True
        )

        json_str = response_text.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        data = json.loads(json_str)
        return {
            "PERSONAL_HOOK": data.get("PERSONAL_HOOK", f"I came across {contact.company or 'your team'} and was impressed by your engineering focus."),
            "RELEVANT_PROJECT_LINE": data.get("RELEVANT_PROJECT_LINE", f"I recently built projects relevant to {contact.role or 'software development'} focusing on scalability and performance."),
            "WHY_THIS_COMPANY": data.get("WHY_THIS_COMPANY", f"I am particularly drawn to {contact.company or 'your team'}'s engineering culture.")
        }
    except Exception as e:
        logger.warning(f"LLM personalizer fallback due to error: {e}")
        return {
            "PERSONAL_HOOK": f"I noticed {contact.company or 'your company'}'s work in software engineering.",
            "RELEVANT_PROJECT_LINE": f"I have hands-on experience building web and backend applications.",
            "WHY_THIS_COMPANY": f"I am eager to contribute to {contact.company or 'your team'}."
        }
