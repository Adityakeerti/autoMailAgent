import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Contact, Template, ContextProfile, Setting
from app.services.personalizer import generate_personalized_placeholders, _company_confidence

logger = logging.getLogger("renderer")

async def render_contact_email(contact_id: int, template_id: Optional[int], db: AsyncSession) -> Contact:
    res_c = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = res_c.scalar_one_or_none()
    if not contact:
        raise ValueError("Contact not found")

    user_id = contact.user_id

    # Get template
    template = None
    if template_id:
        res_t = await db.execute(select(Template).where(Template.id == template_id, Template.user_id == user_id))
        template = res_t.scalar_one_or_none()
    else:
        # If the contact is generic, fetch the Generic Company Outreach template first
        if contact.status in ["generic_new", "generic_queued"]:
            res_t = await db.execute(select(Template).where(Template.user_id == user_id, Template.category == "Generic Company Outreach"))
            template = res_t.scalar_one_or_none()
        
        if not template:
            res_t = await db.execute(select(Template).where(Template.user_id == user_id).limit(1))
            template = res_t.scalar_one_or_none()

    if not template:
        raise ValueError("No template available for user")

    # Fetch context profile static data
    res_p = await db.execute(select(ContextProfile).where(ContextProfile.user_id == user_id))
    prof = res_p.scalar_one_or_none()

    user_name = (contact.user.email.split("@")[0].title()) if contact.user and contact.user.email else "Applicant"
    portfolio_url = (prof.portfolio_url if prof and prof.portfolio_url else "https://portfolio.dev")
    github_url = (prof.github_url if prof and prof.github_url else "https://github.com")

    # Generate dynamic placeholders or bypass for generic template/contacts
    is_generic = contact.status in ["generic_new", "generic_queued"] or template.category == "Generic Company Outreach"
    if is_generic:
        dynamic_placeholders = {}
    else:
        dynamic_placeholders = await generate_personalized_placeholders(contact, template, db)

    # Static map
    company_display = contact.company if _company_confidence(contact.company) == "high" else "your company"
    placeholder_map = {
        "RECIPIENT_NAME": contact.name or "Hiring Manager",
        "COMPANY": company_display,
        "ROLE_TITLE": contact.role or "Software Engineer",
        "USER_NAME": user_name,
        "PORTFOLIO_URL": portfolio_url,
        "GITHUB_URL": github_url,
        "PERSONAL_HOOK": dynamic_placeholders.get("PERSONAL_HOOK", ""),
        "RELEVANT_PROJECT_LINE": dynamic_placeholders.get("RELEVANT_PROJECT_LINE", ""),
        "WHY_THIS_COMPANY": dynamic_placeholders.get("WHY_THIS_COMPANY", "")
    }

    subject = template.subject_template
    body = template.body_template

    for key, val in placeholder_map.items():
        subject = subject.replace(f"{{{{{key}}}}}", str(val))
        body = body.replace(f"{{{{{key}}}}}", str(val))

    contact.subject = subject
    contact.body = body
    contact.personalized_data = dynamic_placeholders
    
    if is_generic:
        contact.status = "generic_queued" if contact.status == "generic_new" else contact.status
    else:
        contact.status = "personalized"

    # Check user send mode
    res_st = await db.execute(select(Setting).where(Setting.user_id == user_id))
    st = res_st.scalar_one_or_none()
    if st and st.send_mode == "auto":
        contact.status = "generic_queued" if is_generic else "queued"

    await db.commit()
    await db.refresh(contact)
    return contact
