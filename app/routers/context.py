from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_db
from app.models import User, ContextProfile, ContextExperience, ContextProject, ContextAchievement, JobPreference
from app.security import get_current_user

router = APIRouter(prefix="/context", tags=["Context Layer"])

# --- Schemas ---
class ProfileSchema(BaseModel):
    role_title: Optional[str] = None
    full_name: Optional[str] = None
    grad_year: Optional[str] = None
    portfolio_url: Optional[str] = None
    github_url: Optional[str] = None
    email: Optional[str] = None
    resume_link: Optional[str] = None

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
        full_name=cp.full_name,
        grad_year=cp.grad_year,
        portfolio_url=cp.portfolio_url,
        github_url=cp.github_url,
        email=cp.email,
        resume_link=cp.resume_link
    )

@router.put("/profile", response_model=ProfileSchema)
async def update_profile(data: ProfileSchema, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ContextProfile).where(ContextProfile.user_id == current_user.id))
    cp = res.scalar_one_or_none()
    if not cp:
        cp = ContextProfile(user_id=current_user.id)
        db.add(cp)

    if data.role_title is not None: cp.role_title = data.role_title
    if data.full_name is not None: cp.full_name = data.full_name
    if data.grad_year is not None: cp.grad_year = data.grad_year
    if data.portfolio_url is not None: cp.portfolio_url = data.portfolio_url
    if data.github_url is not None: cp.github_url = data.github_url
    if data.email is not None: cp.email = data.email
    if data.resume_link is not None: cp.resume_link = data.resume_link

    await db.commit()
    await db.refresh(cp)
    return ProfileSchema(
        role_title=cp.role_title,
        full_name=cp.full_name,
        grad_year=cp.grad_year,
        portfolio_url=cp.portfolio_url,
        github_url=cp.github_url,
        email=cp.email,
        resume_link=cp.resume_link
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

@router.put("/experience/{exp_id}", response_model=ExperienceResponse)
async def update_experience(exp_id: int, data: ExperienceCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ContextExperience).where(ContextExperience.id == exp_id, ContextExperience.user_id == current_user.id))
    exp = res.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Item not found")
    exp.title = data.title
    exp.dates = data.dates
    exp.one_liner = data.one_liner
    exp.stack = data.stack
    exp.tags = data.tags
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

@router.put("/projects/{proj_id}", response_model=ProjectResponse)
async def update_project(proj_id: int, data: ProjectCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ContextProject).where(ContextProject.id == proj_id, ContextProject.user_id == current_user.id))
    proj = res.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Item not found")
    proj.title = data.title
    proj.dates = data.dates
    proj.one_liner = data.one_liner
    proj.stack = data.stack
    proj.tags = data.tags
    proj.link = data.link
    proj.live_link = data.live_link
    proj.note = data.note
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

@router.put("/achievements/{ach_id}", response_model=AchievementResponse)
async def update_achievement(ach_id: int, data: AchievementCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ContextAchievement).where(ContextAchievement.id == ach_id, ContextAchievement.user_id == current_user.id))
    ach = res.scalar_one_or_none()
    if not ach:
        raise HTTPException(status_code=404, detail="Item not found")
    ach.text = data.text
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


# --- Job Preferences ---
class JobPreferenceSchema(BaseModel):
    role_1: Optional[str] = None
    role_2: Optional[str] = None
    role_3: Optional[str] = None
    min_lpa: Optional[float] = None
    max_lpa: Optional[float] = None
    locations: Optional[str] = None
    experience_level: Optional[str] = None

@router.get("/job-preferences", response_model=JobPreferenceSchema)
async def get_job_preferences(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(JobPreference).where(JobPreference.user_id == current_user.id))
    jp = res.scalar_one_or_none()
    if not jp:
        return JobPreferenceSchema()
    return JobPreferenceSchema(
        role_1=jp.role_1, role_2=jp.role_2, role_3=jp.role_3,
        min_lpa=jp.min_lpa, max_lpa=jp.max_lpa,
        locations=jp.locations, experience_level=jp.experience_level
    )

@router.put("/job-preferences", response_model=JobPreferenceSchema)
async def update_job_preferences(data: JobPreferenceSchema, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(JobPreference).where(JobPreference.user_id == current_user.id))
    jp = res.scalar_one_or_none()
    if not jp:
        jp = JobPreference(user_id=current_user.id)
        db.add(jp)
    if data.role_1 is not None: jp.role_1 = data.role_1
    if data.role_2 is not None: jp.role_2 = data.role_2
    if data.role_3 is not None: jp.role_3 = data.role_3
    if data.min_lpa is not None: jp.min_lpa = data.min_lpa
    if data.max_lpa is not None: jp.max_lpa = data.max_lpa
    if data.locations is not None: jp.locations = data.locations
    if data.experience_level is not None: jp.experience_level = data.experience_level
    await db.commit()
    await db.refresh(jp)
    return JobPreferenceSchema(
        role_1=jp.role_1, role_2=jp.role_2, role_3=jp.role_3,
        min_lpa=jp.min_lpa, max_lpa=jp.max_lpa,
        locations=jp.locations, experience_level=jp.experience_level
    )
