from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, Setting, Template
from app.security import hash_password, verify_password, create_access_token
from app.services.default_templates import DEFAULT_TEMPLATES

router = APIRouter(prefix="/auth", tags=["Auth"])

class UserSignup(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class GoogleAuthRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    google_id: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserSignup, db: AsyncSession = Depends(get_db)):
    clean_email = user_data.email.strip().lower()
    existing = await db.execute(select(User).where(User.email == clean_email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=clean_email,
        password_hash=hash_password(user_data.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    db.add(Setting(user_id=new_user.id))

    for tmpl in DEFAULT_TEMPLATES:
        db.add(Template(
            user_id=new_user.id,
            category=tmpl["category"],
            subject_template=tmpl["subject_template"],
            body_template=tmpl["body_template"]
        ))
    await db.commit()

    token = create_access_token(user_id=new_user.id, email=new_user.email)
    return {"access_token": token, "token_type": "bearer"}

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    clean_email = credentials.email.strip().lower()
    res = await db.execute(select(User).where(User.email == clean_email))
    user = res.scalar_one_or_none()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(user_id=user.id, email=user.email)
    return {"access_token": token, "token_type": "bearer"}

@router.post("/google", response_model=TokenResponse)
async def google_auth(req: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """1-Click Connect with Google Authentication"""
    clean_email = req.email.strip().lower()
    res = await db.execute(select(User).where(User.email == clean_email))
    user = res.scalar_one_or_none()

    if not user:
        # Create user automatically on Google auth
        user = User(
            email=clean_email,
            password_hash=hash_password(f"google_oauth_{clean_email}")
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        db.add(Setting(user_id=user.id, smtp_user=clean_email, imap_user=clean_email, smtp_host="smtp.gmail.com", imap_host="imap.gmail.com"))

        for tmpl in DEFAULT_TEMPLATES:
            db.add(Template(
                user_id=user.id,
                category=tmpl["category"],
                subject_template=tmpl["subject_template"],
                body_template=tmpl["body_template"]
            ))
        await db.commit()

    token = create_access_token(user_id=user.id, email=user.email)
    return {"access_token": token, "token_type": "bearer"}
