from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Contact, ContextProject, ContextExperience

def calculate_tag_overlap(target_tags: List[str], candidate_tags: List[str], text_content: str) -> int:
    score = 0
    c_set = set(t.lower() for t in candidate_tags)
    for tag in target_tags:
        t_low = tag.lower()
        if t_low in c_set:
            score += 3
        elif t_low in text_content.lower():
            score += 1
    return score

async def find_best_matching_context(contact: Contact, db: AsyncSession) -> Tuple[Optional[str], Optional[Any]]:
    """
    Given a contact, find the best matching context entry (project or experience)
    based on tag/role overlap.
    Returns ("project", project_obj) or ("experience", exp_obj) or (None, None).
    """
    user_id = contact.user_id

    # Gather tags from contact role, company, or job posting url
    target_terms = []
    if contact.role: target_terms.extend(contact.role.replace("/", " ").split())
    if contact.company: target_terms.append(contact.company)
    if contact.source: target_terms.append(contact.source)

    # Fetch projects and experiences for user
    res_proj = await db.execute(select(ContextProject).where(ContextProject.user_id == user_id))
    projects = res_proj.scalars().all()

    res_exp = await db.execute(select(ContextExperience).where(ContextExperience.user_id == user_id))
    experiences = res_exp.scalars().all()

    best_score = -1
    best_type = None
    best_item = None

    for p in projects:
        score = calculate_tag_overlap(target_terms, p.tags or [], f"{p.title} {p.one_liner or ''} {' '.join(p.stack or [])}")
        if score > best_score:
            best_score = score
            best_type = "project"
            best_item = p

    for e in experiences:
        score = calculate_tag_overlap(target_terms, e.tags or [], f"{e.title} {e.one_liner or ''} {' '.join(e.stack or [])}")
        if score > best_score:
            best_score = score
            best_type = "experience"
            best_item = e

    if best_item is None:
        # Default fallback to first project or experience if available
        if projects:
            return ("project", projects[0])
        elif experiences:
            return ("experience", experiences[0])
        return (None, None)

    return (best_type, best_item)
