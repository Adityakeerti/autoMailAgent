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

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserSignup, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    existing = await db.execute(select(User).where(User.email == user_data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    new_user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Seed default settings for user
    new_settings = Setting(user_id=new_user.id)
    db.add(new_settings)

    # Seed default 5 templates for user
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
    res = await db.execute(select(User).where(User.email == credentials.email))
    user = res.scalar_one_or_none()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(user_id=user.id, email=user.email)
    return {"access_token": token, "token_type": "bearer"}
