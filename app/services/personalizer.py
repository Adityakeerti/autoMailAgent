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
You are an expert cold email copywriter. Generate high-impact, tailored placeholders for a job application cold email using full technical context.

Strict Tone & Style Rules:
- Tone: Technical, direct, and factual. Focus on actual system architecture, frameworks, algorithms, or technical problems solved.
- Absolute Prohibition: NO generic corporate fluff or superlatives (e.g., "amazing", "revolutionary", "proud to share", "thrilled to connect").
- Project Line: Synthesize 1-2 punchy sentences highlighting the most relevant technical features, tech stack, or engineering achievements from the user's detailed project/experience context.
- Email Word Count: Keep output concise so total email remains under ~120 words.
- Hook Phrasing: Must be unique and domain-specific to the recipient or target company.

Return a JSON object with these exact keys:
{
  "PERSONAL_HOOK": "One short sentence connecting to recipient/company domain.",
  "RELEVANT_PROJECT_LINE": "1-2 sentences highlighting key technical architecture, stack, and problem solved from user context.",
  "WHY_THIS_COMPANY": "One short sentence connecting user's technical background to company mission/tech."
}
"""

PERSONALIZER_SYSTEM_PROMPT_NO_COMPANY = """
You are an expert cold email copywriter. Generate high-impact, tailored placeholders for a job application cold email using full technical context.

IMPORTANT: The company name for this contact is unknown or uncertain. Do NOT invent or guess the company name.
Instead, use generic but warm phrasing like "your team", "your organization", "your engineering team", or "your company".

Strict Tone & Style Rules:
- Tone: Technical, direct, and factual. Focus on actual system architecture, frameworks, algorithms, or technical problems solved.
- Absolute Prohibition: NO generic corporate fluff or superlatives (e.g., "amazing", "revolutionary", "proud to share", "thrilled to connect").
- Do NOT use any company name — use "your team" / "your engineering team" / "your organization" throughout.
- Project Line: Synthesize 1-2 punchy sentences highlighting the most relevant technical features, tech stack, or engineering achievements from the user's detailed project/experience context.
- Email Word Count: Keep output concise so total email remains under ~120 words.

Return a JSON object with these exact keys:
{
  "PERSONAL_HOOK": "One short sentence connecting to the recipient's domain/role, WITHOUT naming the company.",
  "RELEVANT_PROJECT_LINE": "1-2 sentences highlighting key technical architecture, stack, and problem solved from user context.",
  "WHY_THIS_COMPANY": "One short sentence about why the user wants to join this team, WITHOUT naming the company."
}
"""


def _company_confidence(company: Optional[str]) -> str:
    """
    Returns 'high' if company name looks like a real company name,
    'low' if it's a domain-derived guess or looks generic/suspicious.
    'none' if company is missing entirely.
    """
    if not company:
        return "none"
    c = company.strip()
    # Known generic fallbacks that must never be used
    generic = {"target company", "hiring manager", "company", "unknown", "n/a", "na", "recruiter"}
    if c.lower() in generic:
        return "low"
    # If it's just a single word that looks like a domain name part (all lowercase, no spaces)
    # it was likely derived from a URL — lower confidence
    if c == c.lower() and " " not in c and len(c) <= 15:
        return "low"
    return "high"


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
            context_desc = f"Project Title: {context_item.title}\nFull Details & Architecture: {context_item.one_liner}\nTech Stack: {', '.join(context_item.stack or [])}"
        else:
            context_desc = f"Experience Title: {context_item.title}\nFull Details & Achievements: {context_item.one_liner}\nTech Stack: {', '.join(context_item.stack or [])}"

    # --- Company confidence check ---
    confidence = _company_confidence(contact.company)
    use_company_name = confidence == "high"

    if use_company_name:
        system_prompt = PERSONALIZER_SYSTEM_PROMPT
        company_line = f"Target Company: {contact.company}"
    else:
        # Low/no confidence: instruct LLM to not use a company name
        system_prompt = PERSONALIZER_SYSTEM_PROMPT_NO_COMPANY
        company_line = "Target Company: [UNKNOWN — do NOT invent a company name, use 'your team' phrasing]"

    user_prompt = f"""
Target Recipient: {contact.name or 'Hiring Manager'}
{company_line}
Target Role: {contact.role or 'Software Engineer'}
Source/Job Link: {contact.job_posting_url or 'N/A'}

Full User Engineering Context:
{context_desc or 'General Software Engineering experience building web applications and backend systems.'}
{avoid_clause}
"""

    # Safe fallback values that respect confidence
    safe_company = contact.company if use_company_name else "your team"
    safe_company_ref = contact.company if use_company_name else "your engineering team"

    try:
        response_text = await llm_service.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            high_tier=False,
            json_mode=True
        )

        json_str = response_text.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        data = json.loads(json_str)
        return {
            "PERSONAL_HOOK": data.get("PERSONAL_HOOK", f"I came across {safe_company} and was impressed by your engineering focus."),
            "RELEVANT_PROJECT_LINE": data.get("RELEVANT_PROJECT_LINE", f"I recently built projects relevant to {contact.role or 'software development'} focusing on scalability and performance."),
            "WHY_THIS_COMPANY": data.get("WHY_THIS_COMPANY", f"I am particularly drawn to {safe_company_ref}'s engineering culture.")
        }
    except Exception as e:
        logger.warning(f"LLM personalizer fallback due to error: {e}")
        return {
            "PERSONAL_HOOK": f"I noticed {safe_company}'s work in software engineering.",
            "RELEVANT_PROJECT_LINE": f"I have hands-on experience building web and backend applications.",
            "WHY_THIS_COMPANY": f"I am eager to contribute to {safe_company_ref}."
        }
