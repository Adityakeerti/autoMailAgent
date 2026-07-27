from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_db
from app.models import User, ContextProfile, ContextExperience, ContextProject, ContextAchievement
from app.security import get_current_user

router = APIRouter(prefix="/context", tags=["Context Layer"])

# --- Schemas ---
class ProfileSchema(BaseModel):
    role_title: Optional[str] = None
    grad_year: Optional[str] = None
    portfolio_url: Optional[str] = None
    github_url: Optional[str] = None
    email: Optional[str] = None

class ExperienceCreate(BaseModel):
    title: str
    dates: Optional[str] = None
    one_liner: Optional[str] = None
    stack: List[str] = []
    tags: List[str] = []

class ExperienceResponse(ExperienceCreate):
    id: int
    user_id: int

class ProjectCreate(BaseModel):
    title: str
    dates: Optional[str] = None
    one_liner: Optional[str] = None
    stack: List[str] = []
    tags: List[str] = []
    link: Optional[str] = None
    live_link: Optional[str] = None
    note: Optional[str] = None

class ProjectResponse(ProjectCreate):
    id: int
    user_id: int

class AchievementCreate(BaseModel):
    text: str

class AchievementResponse(AchievementCreate):
    id: int
    user_id: int

# --- Profile Routes ---
@router.get("/profile", response_model=ProfileSchema)
async def get_profile(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ContextProfile).where(ContextProfile.user_id == current_user.id))
    cp = res.scalar_one_or_none()
    if not cp:
        return ProfileSchema()
    return ProfileSchema(
        role_title=cp.role_title,
        grad_year=cp.grad_year,
        portfolio_url=cp.portfolio_url,
        github_url=cp.github_url,
        email=cp.email
    )

@router.put("/profile", response_model=ProfileSchema)
async def update_profile(data: ProfileSchema, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ContextProfile).where(ContextProfile.user_id == current_user.id))
    cp = res.scalar_one_or_none()
    if not cp:
        cp = ContextProfile(user_id=current_user.id)
        db.add(cp)

    if data.role_title is not None: cp.role_title = data.role_title
    if data.grad_year is not None: cp.grad_year = data.grad_year
    if data.portfolio_url is not None: cp.portfolio_url = data.portfolio_url
    if data.github_url is not None: cp.github_url = data.github_url
    if data.email is not None: cp.email = data.email

    await db.commit()
    await db.refresh(cp)
    return ProfileSchema(
        role_title=cp.role_title,
        grad_year=cp.grad_year,
        portfolio_url=cp.portfolio_url,
        github_url=cp.github_url,
        email=cp.email
    )

# --- Experience Routes ---
@router.get("/experience", response_model=List[ExperienceResponse])
async def list_experience(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ContextExperience).where(ContextExperience.user_id == current_user.id))
    items = res.scalars().all()
    return [ExperienceResponse(id=item.id, user_id=item.user_id, title=item.title, dates=item.dates, one_liner=item.one_liner, stack=item.stack or [], tags=item.tags or []) for item in items]

@router.post("/experience", response_model=ExperienceResponse, status_code=status.HTTP_201_CREATED)
async def create_experience(data: ExperienceCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    exp = ContextExperience(
        user_id=current_user.id,
        title=data.title,
        dates=data.dates,
        one_liner=data.one_liner,
        stack=data.stack,
        tags=data.tags
    )
    db.add(exp)
    await db.commit()
    await db.refresh(exp)
    return ExperienceResponse(id=exp.id, user_id=exp.user_id, title=exp.title, dates=exp.dates, one_liner=exp.one_liner, stack=exp.stack or [], tags=exp.tags or [])

@router.delete("/experience/{exp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experience(exp_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ContextExperience).where(ContextExperience.id == exp_id, ContextExperience.user_id == current_user.id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()

# --- Projects Routes ---
@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ContextProject).where(ContextProject.user_id == current_user.id))
    items = res.scalars().all()
    return [ProjectResponse(id=item.id, user_id=item.user_id, title=item.title, dates=item.dates, one_liner=item.one_liner, stack=item.stack or [], tags=item.tags or [], link=item.link, live_link=item.live_link, note=item.note) for item in items]

@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(data: ProjectCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    proj = ContextProject(
        user_id=current_user.id,
        title=data.title,
        dates=data.dates,
        one_liner=data.one_liner,
        stack=data.stack,
        tags=data.tags,
        link=data.link,
        live_link=data.live_link,
        note=data.note
    )
    db.add(proj)
    await db.commit()
    await db.refresh(proj)
    return ProjectResponse(id=proj.id, user_id=proj.user_id, title=proj.title, dates=proj.dates, one_liner=proj.one_liner, stack=proj.stack or [], tags=proj.tags or [], link=proj.link, live_link=proj.live_link, note=proj.note)

@router.delete("/projects/{proj_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(proj_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ContextProject).where(ContextProject.id == proj_id, ContextProject.user_id == current_user.id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()

# --- Achievements Routes ---
@router.get("/achievements", response_model=List[AchievementResponse])
async def list_achievements(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ContextAchievement).where(ContextAchievement.user_id == current_user.id))
    items = res.scalars().all()
    return [AchievementResponse(id=item.id, user_id=item.user_id, text=item.text) for item in items]

@router.post("/achievements", response_model=AchievementResponse, status_code=status.HTTP_201_CREATED)
async def create_achievement(data: AchievementCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ach = ContextAchievement(user_id=current_user.id, text=data.text)
    db.add(ach)
    await db.commit()
    await db.refresh(ach)
    return AchievementResponse(id=ach.id, user_id=ach.user_id, text=ach.text)

@router.delete("/achievements/{ach_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_achievement(ach_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ContextAchievement).where(ContextAchievement.id == ach_id, ContextAchievement.user_id == current_user.id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()
