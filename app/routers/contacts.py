from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from app.database import get_db
from app.models import User, Contact
from app.security import get_current_user

router = APIRouter(prefix="/contacts", tags=["Contacts"])

class ContactCreate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    source: Optional[str] = "manual"
    job_posting_url: Optional[str] = None
    email: EmailStr
    linkedin_url: Optional[str] = None

class ChannelMetrics(BaseModel):
    source: str
    leads_found: int
    real_name_count: int
    generic_count: int
    valid_count: int
    bounced_count: int

class StatusUpdate(BaseModel):
    status: str

class ContactResponse(BaseModel):
    id: int
    user_id: int
    name: Optional[str]
    company: Optional[str]
    role: Optional[str]
    source: Optional[str]
    job_posting_url: Optional[str]
    email: str
    linkedin_url: Optional[str]
    status: str
    subject: Optional[str]
    body: Optional[str]
    discovered_at: str

@router.get("", response_model=List[ContactResponse])
async def list_contacts(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Contact).where(Contact.user_id == current_user.id))
    items = res.scalars().all()
    return [
        ContactResponse(
            id=c.id,
            user_id=c.user_id,
            name=c.name,
            company=c.company,
            role=c.role,
            source=c.source,
            job_posting_url=c.job_posting_url,
            email=c.email,
            linkedin_url=c.linkedin_url,
            status=c.status,
            subject=c.subject,
            body=c.body,
            discovered_at=c.discovered_at.isoformat() + "Z"
        )
        for c in items
    ]

@router.get("/metrics", response_model=List[ChannelMetrics])
async def get_contacts_metrics(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = (
        select(
            Contact.source,
            func.count(Contact.id).label("leads_found"),
            func.sum(
                case(
                    (Contact.name != "Hiring Manager", 1),
                    else_=0
                )
            ).label("real_name_count"),
            func.sum(
                case(
                    (Contact.name == "Hiring Manager", 1),
                    else_=0
                )
            ).label("generic_count"),
            func.sum(
                case(
                    (Contact.status != "bounced", 1),
                    else_=0
                )
            ).label("valid_count"),
            func.sum(
                case(
                    (Contact.status == "bounced", 1),
                    else_=0
                )
            ).label("bounced_count")
        )
        .where(Contact.user_id == current_user.id)
        .group_by(Contact.source)
    )
    res = await db.execute(stmt)
    rows = res.all()
    
    metrics = []
    for row in rows:
        source = row.source or "unknown"
        metrics.append(ChannelMetrics(
            source=source,
            leads_found=row.leads_found or 0,
            real_name_count=int(row.real_name_count or 0),
            generic_count=int(row.generic_count or 0),
            valid_count=int(row.valid_count or 0),
            bounced_count=int(row.bounced_count or 0)
        ))
    return metrics

@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(data: ContactCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    c = Contact(
        user_id=current_user.id,
        name=data.name,
        company=data.company,
        role=data.role,
        source=data.source,
        job_posting_url=data.job_posting_url,
        email=data.email,
        linkedin_url=data.linkedin_url,
        status="new"
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return ContactResponse(
        id=c.id,
        user_id=c.user_id,
        name=c.name,
        company=c.company,
        role=c.role,
        source=c.source,
        job_posting_url=c.job_posting_url,
        email=c.email,
        linkedin_url=c.linkedin_url,
        status=c.status,
        subject=c.subject,
        body=c.body,
        discovered_at=c.discovered_at.isoformat() + "Z"
    )

@router.put("/{contact_id}/status", response_model=ContactResponse)
async def update_contact_status(contact_id: int, data: StatusUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    valid_statuses = ["new", "personalized", "queued", "sent", "replied", "bounced", "generic_new", "generic_queued"]
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")

    res = await db.execute(select(Contact).where(Contact.id == contact_id, Contact.user_id == current_user.id))
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Contact not found")

    c.status = data.status
    await db.commit()
    await db.refresh(c)
    return ContactResponse(
        id=c.id,
        user_id=c.user_id,
        name=c.name,
        company=c.company,
        role=c.role,
        source=c.source,
        job_posting_url=c.job_posting_url,
        email=c.email,
        linkedin_url=c.linkedin_url,
        status=c.status,
        subject=c.subject,
        body=c.body,
        discovered_at=c.discovered_at.isoformat() + "Z"
    )

@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(contact_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Contact).where(Contact.id == contact_id, Contact.user_id == current_user.id))
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Contact not found")
    await db.delete(c)
    await db.commit()
