from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db, AsyncSessionLocal
from app.models import User, Resume
from app.security import get_current_user
from app.services.storage import storage_service
from app.services.parser import parse_and_populate_resume

router = APIRouter(prefix="/resume", tags=["Resume"])

class ResumeResponse(BaseModel):
    id: int
    user_id: int
    file_name: str
    file_url: str
    uploaded_at: str
    parsed_status: str

async def _bg_parse_wrapper(resume_id: int, mode: str):
    async with AsyncSessionLocal() as db:
        await parse_and_populate_resume(resume_id, db, mode=mode)

@router.post("/upload", response_model=ResumeResponse)
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    mode: str = Query("keep_unique", description="Parse mode: 'replace' (remove old info) or 'keep_unique' (keep unique items)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    if mode not in ["replace", "keep_unique"]:
        raise HTTPException(status_code=400, detail="Invalid mode. Must be 'replace' or 'keep_unique'")

    file_path = await storage_service.save_resume(current_user.id, file)

    resume = Resume(
        user_id=current_user.id,
        file_url=file_path,
        file_name=file.filename,
        parsed_status="pending"
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    # Trigger background parse job with selected mode
    background_tasks.add_task(_bg_parse_wrapper, resume.id, mode)

    return ResumeResponse(
        id=resume.id,
        user_id=resume.user_id,
        file_name=resume.file_name or "resume.pdf",
        file_url=resume.file_url,
        uploaded_at=resume.uploaded_at.isoformat() + "Z",
        parsed_status=resume.parsed_status
    )

@router.get("", response_model=List[ResumeResponse])
async def list_resumes(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Resume).where(Resume.user_id == current_user.id))
    items = res.scalars().all()
    return [
        ResumeResponse(
            id=r.id,
            user_id=r.user_id,
            file_name=r.file_name or "resume.pdf",
            file_url=r.file_url,
            uploaded_at=r.uploaded_at.isoformat() + "Z",
            parsed_status=r.parsed_status
        )
        for r in items
    ]

@router.post("/{resume_id}/parse", response_model=ResumeResponse)
async def trigger_parse(
    resume_id: int,
    background_tasks: BackgroundTasks,
    mode: str = Query("keep_unique", description="Parse mode: 'replace' or 'keep_unique'"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id))
    resume = res.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    resume.parsed_status = "pending"
    await db.commit()
    await db.refresh(resume)

    background_tasks.add_task(_bg_parse_wrapper, resume.id, mode)

    return ResumeResponse(
        id=resume.id,
        user_id=resume.user_id,
        file_name=resume.file_name or "resume.pdf",
        file_url=resume.file_url,
        uploaded_at=resume.uploaded_at.isoformat() + "Z",
        parsed_status=resume.parsed_status
    )

@router.delete("/{resume_id}", status_code=200)
async def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id))
    resume = res.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Delete physical file from disk
    storage_service.delete_resume_file(resume.file_url)

    # Delete DB row
    await db.delete(resume)
    await db.commit()

    return {"message": f"Resume {resume_id} deleted successfully"}
