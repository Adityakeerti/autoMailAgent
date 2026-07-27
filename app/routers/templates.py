from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, Template
from app.security import get_current_user

router = APIRouter(prefix="/templates", tags=["Templates"])

class TemplateCreate(BaseModel):
    category: str
    subject_template: str
    body_template: str

class TemplateUpdate(BaseModel):
    category: Optional[str] = None
    subject_template: Optional[str] = None
    body_template: Optional[str] = None

class TemplateResponse(TemplateCreate):
    id: int
    user_id: int

@router.get("", response_model=List[TemplateResponse])
async def list_templates(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Template).where(Template.user_id == current_user.id))
    items = res.scalars().all()
    return [
        TemplateResponse(
            id=t.id,
            user_id=t.user_id,
            category=t.category,
            subject_template=t.subject_template,
            body_template=t.body_template
        )
        for t in items
    ]

@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(data: TemplateCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    tmpl = Template(
        user_id=current_user.id,
        category=data.category,
        subject_template=data.subject_template,
        body_template=data.body_template
    )
    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)
    return TemplateResponse(
        id=tmpl.id,
        user_id=tmpl.user_id,
        category=tmpl.category,
        subject_template=tmpl.subject_template,
        body_template=tmpl.body_template
    )

@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(template_id: int, data: TemplateUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Template).where(Template.id == template_id, Template.user_id == current_user.id))
    tmpl = res.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")

    if data.category is not None: tmpl.category = data.category
    if data.subject_template is not None: tmpl.subject_template = data.subject_template
    if data.body_template is not None: tmpl.body_template = data.body_template

    await db.commit()
    await db.refresh(tmpl)
    return TemplateResponse(
        id=tmpl.id,
        user_id=tmpl.user_id,
        category=tmpl.category,
        subject_template=tmpl.subject_template,
        body_template=tmpl.body_template
    )

@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(template_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Template).where(Template.id == template_id, Template.user_id == current_user.id))
    tmpl = res.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")

    await db.delete(tmpl)
    await db.commit()
