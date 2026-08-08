from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, Contact, Setting, SendLog
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
    job_posting_url: Optional[str] = None

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
            personalized_data=c.personalized_data,
            job_posting_url=c.job_posting_url
        )
        for c in items
    ]

@router.get("/generic", response_model=List[QueueItemResponse])
async def list_generic_queue(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Contact).where(
            Contact.user_id == current_user.id,
            Contact.status.in_(["generic_new", "generic_queued"])
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
            personalized_data=c.personalized_data,
            job_posting_url=c.job_posting_url
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
        personalized_data=updated_contact.personalized_data,
        job_posting_url=updated_contact.job_posting_url
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
    status_before = c.status
    if not c.subject or not c.body:
        c = await render_contact_email(c.id, None, db)

    c.status = "generic_queued" if (status_before == "generic_new" or c.status == "generic_queued") else "queued"
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
        personalized_data=c.personalized_data,
        job_posting_url=c.job_posting_url
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

class BulkActionRequest(BaseModel):
    ids: List[int]

@router.post("/bulk-approve")
async def bulk_approve_queue_items(
    data: BulkActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(Contact).where(Contact.id.in_(data.ids), Contact.user_id == current_user.id)
    )
    contacts = res.scalars().all()
    
    for c in contacts:
        status_before = c.status
        if not c.subject or not c.body:
            c = await render_contact_email(c.id, None, db)
        c.status = "generic_queued" if (status_before == "generic_new" or c.status == "generic_queued") else "queued"
    
    await db.commit()
    return {"message": f"Successfully approved {len(contacts)} contacts"}

@router.post("/bulk-reject")
async def bulk_reject_queue_items(
    data: BulkActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(Contact).where(Contact.id.in_(data.ids), Contact.user_id == current_user.id)
    )
    contacts = res.scalars().all()
    
    for c in contacts:
        c.status = "rejected"
        
    await db.commit()
    return {"message": f"Successfully rejected {len(contacts)} contacts"}

@router.post("/{contact_id}/send", response_model=QueueItemResponse)
async def send_queued_item(
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

    # Send immediately
    success = await send_contact_email_via_smtp(c, db)
    if not success:
        log_res = await db.execute(
            select(SendLog).where(SendLog.contact_id == c.id).order_by(SendLog.sent_at.desc())
        )
        last_log = log_res.scalars().first()
        err_msg = last_log.status if last_log else "Failed to send email"
        raise HTTPException(
            status_code=400,
            detail=f"Email sending failed: {err_msg}"
        )

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
        personalized_data=c.personalized_data,
        job_posting_url=c.job_posting_url
    )
