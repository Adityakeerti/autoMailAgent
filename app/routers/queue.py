from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, Contact, Setting
from app.security import get_current_user
from app.services.renderer import render_contact_email
from app.services.smtp_sender import send_contact_email_via_smtp

router = APIRouter(prefix="/queue", tags=["Send Queue & Approval"])

class QueueItemResponse(BaseModel):
    id: int
    user_id: int
    name: Optional[str]
    company: Optional[str]
    role: Optional[str]
    email: str
    status: str
    subject: Optional[str]
    body: Optional[str]
    personalized_data: Optional[dict]

@router.get("", response_model=List[QueueItemResponse])
async def list_queue(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Contact).where(
            Contact.user_id == current_user.id,
            Contact.status.in_(["new", "personalized", "queued"])
        )
    )
    items = res.scalars().all()
    return [
        QueueItemResponse(
            id=c.id,
            user_id=c.user_id,
            name=c.name,
            company=c.company,
            role=c.role,
            email=c.email,
            status=c.status,
            subject=c.subject,
            body=c.body,
            personalized_data=c.personalized_data
        )
        for c in items
    ]

@router.post("/{contact_id}/personalize", response_model=QueueItemResponse)
async def personalize_contact(
    contact_id: int,
    template_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Contact).where(Contact.id == contact_id, Contact.user_id == current_user.id))
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Contact not found")

    updated_contact = await render_contact_email(c.id, template_id, db)
    return QueueItemResponse(
        id=updated_contact.id,
        user_id=updated_contact.user_id,
        name=updated_contact.name,
        company=updated_contact.company,
        role=updated_contact.role,
        email=updated_contact.email,
        status=updated_contact.status,
        subject=updated_contact.subject,
        body=updated_contact.body,
        personalized_data=updated_contact.personalized_data
    )

@router.post("/{contact_id}/approve", response_model=QueueItemResponse)
async def approve_queued_item(
    contact_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Contact).where(Contact.id == contact_id, Contact.user_id == current_user.id))
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Contact not found")

    # If not yet personalized, render first
    if not c.subject or not c.body:
        c = await render_contact_email(c.id, None, db)

    c.status = "queued"
    await db.commit()
    await db.refresh(c)

    return QueueItemResponse(
        id=c.id,
        user_id=c.user_id,
        name=c.name,
        company=c.company,
        role=c.role,
        email=c.email,
        status=c.status,
        subject=c.subject,
        body=c.body,
        personalized_data=c.personalized_data
    )

@router.post("/{contact_id}/reject")
async def reject_queued_item(
    contact_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Contact).where(Contact.id == contact_id, Contact.user_id == current_user.id))
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Contact not found")

    c.status = "rejected"
    await db.commit()
    return {"message": f"Contact {contact_id} rejected and removed from send queue"}
