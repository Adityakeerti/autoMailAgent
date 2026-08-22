import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Contact, Template, ContextProfile, Setting
from app.services.personalizer import generate_personalized_placeholders, _company_confidence

logger = logging.getLogger("renderer")

async def render_contact_email(contact_id: int, template_id: Optional[int], db: AsyncSession) -> Contact:
    from sqlalchemy.orm import selectinload
    res_c = await db.execute(
        select(Contact)
        .where(Contact.id == contact_id)
        .options(selectinload(Contact.user))
    )
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
        # Check if the contact is generic
        is_generic_contact = contact.status in ["generic_new", "generic_queued"] or contact.email.lower().startswith(("careers@", "jobs@", "info@", "hr@", "recruiting@", "recruitment@", "hello@", "contact@", "team@"))
        
        if is_generic_contact:
            res_t = await db.execute(select(Template).where(Template.user_id == user_id, Template.category == "Generic Company Outreach"))
            template = res_t.scalars().first()
        else:
            # Check hiring status (is hiring if job_posting_url is set and not empty)
            is_hiring = contact.job_posting_url is not None and contact.job_posting_url != ""

            # Check role to determine if recipient is a technical lead/engineer or recruiter/HR
            role_lower = (contact.role or "").lower()
            is_tech = any(kw in role_lower for kw in ["lead", "manager", "director", "vp", "cto", "architect", "engineer", "developer", "principal", "staff", "head", "technical"])
            is_recruiter = any(kw in role_lower for kw in ["recruiter", "talent", "hr", "people", "hiring", "acquisition", "staffing"])

            if is_tech and not is_recruiter:
                if is_hiring:
                    # Referral Ask is the preferred flow for hiring tech leads
                    res_t = await db.execute(select(Template).where(Template.user_id == user_id, Template.category == "Referral Ask"))
                    template = res_t.scalars().first()
                if not template:
                    # Pitch ourselves directly for non-hiring or fallback
                    res_t = await db.execute(select(Template).where(Template.user_id == user_id, Template.category == "Direct Tech Lead Pitch"))
                    template = res_t.scalars().first()
            elif is_recruiter:
                if is_hiring:
                    # Cold Apply Direct is preferred for hiring recruiters
                    res_t = await db.execute(select(Template).where(Template.user_id == user_id, Template.category == "Cold Apply Direct"))
                    template = res_t.scalars().first()
                if not template:
                    # Recruiter / HR Outreach is fallback or non-hiring recruiter outreach
                    res_t = await db.execute(select(Template).where(Template.user_id == user_id, Template.category == "Recruiter / HR Outreach"))
                    template = res_t.scalars().first()

        # Fallback to the first available template if no category-specific matches
        if not template:
            res_t = await db.execute(select(Template).where(Template.user_id == user_id).limit(1))
            template = res_t.scalars().first()

    if not template:
        raise ValueError("No template available for user")

    # Fetch context profile static data
    res_p = await db.execute(select(ContextProfile).where(ContextProfile.user_id == user_id))
    prof = res_p.scalar_one_or_none()

    user_name = prof.full_name if prof and prof.full_name else ((contact.user.email.split("@")[0].title()) if contact.user and contact.user.email else "Applicant")
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
    resume_link = prof.resume_link if prof and prof.resume_link else ""
    placeholder_map = {
        "RECIPIENT_NAME": contact.name or "Hiring Manager",
        "COMPANY": company_display,
        "ROLE_TITLE": contact.role or "Software Engineer",
        "USER_NAME": user_name,
        "PORTFOLIO_URL": portfolio_url,
        "GITHUB_URL": github_url,
        "RESUME_LINK": resume_link,
        "PERSONAL_HOOK": dynamic_placeholders.get("PERSONAL_HOOK", ""),
        "RELEVANT_PROJECT_LINE": dynamic_placeholders.get("RELEVANT_PROJECT_LINE", ""),
        "WHY_THIS_COMPANY": dynamic_placeholders.get("WHY_THIS_COMPANY", "")
    }
 
    subject = template.subject_template
    body = template.body_template
 
    for key, val in placeholder_map.items():
        subject = subject.replace(f"{{{{{key}}}}}", str(val))
        body = body.replace(f"{{{{{key}}}}}", str(val))

    # Append resume link at the bottom if not present as placeholder
    if resume_link and "{{RESUME_LINK}}" not in template.body_template:
        body += f"\n\nResume: {resume_link}"
 
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
