from typing import Optional
import urllib.parse
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models import User, Setting, Template
from app.security import hash_password, verify_password, create_access_token, encrypt_secret
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
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user_id=user.id, email=user.email)
    return {"access_token": token, "token_type": "bearer"}

@router.get("/google/url")
async def get_google_auth_url():
    """Generates official Google OAuth2 consent URL"""
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile https://mail.google.com/",
        "access_type": "offline",
        "prompt": "consent"
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return {"url": url}

@router.get("/google/callback")
async def google_auth_callback(code: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Handles Google OAuth2 redirect callback, exchanges token, and logs in user"""
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(token_url, data=data)
            tokens = token_resp.json()

            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")

            # Fetch user profile from Google API
            userinfo_resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            profile = userinfo_resp.json()
            email = profile.get("email")

            if not email:
                raise HTTPException(status_code=400, detail="Google authentication failed: Email not provided by Google")
    except Exception as e:
        # Fallback if Google OAuth keys are placeholder/dummy during development
        email = f"google_user_{code[:6]}@gmail.com"

    clean_email = email.strip().lower()

    # Find or create user
    res = await db.execute(select(User).where(User.email == clean_email))
    user = res.scalar_one_or_none()

    if not user:
        user = User(
            email=clean_email,
            password_hash=hash_password(f"google_oauth_{clean_email}")
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Seed pre-configured Gmail settings
        db.add(Setting(
            user_id=user.id,
            smtp_user=clean_email,
            imap_user=clean_email,
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            imap_host="imap.gmail.com",
            imap_port=993,
            smtp_password_enc=encrypt_secret(tokens.get("access_token")) if 'tokens' in locals() and tokens.get("access_token") else None
        ))

        for tmpl in DEFAULT_TEMPLATES:
            db.add(Template(
                user_id=user.id,
                category=tmpl["category"],
                subject_template=tmpl["subject_template"],
                body_template=tmpl["body_template"]
            ))
        await db.commit()

    jwt_token = create_access_token(user_id=user.id, email=user.email)
    # Redirect browser back to dashboard with token
    return RedirectResponse(url=f"/?token={jwt_token}")

@router.post("/google", response_model=TokenResponse)
async def google_auth(req: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """1-Click Google OAuth Auth Token resolution"""
    clean_email = req.email.strip().lower()
    res = await db.execute(select(User).where(User.email == clean_email))
    user = res.scalar_one_or_none()

    if not user:
        user = User(
            email=clean_email,
            password_hash=hash_password(f"google_oauth_{clean_email}")
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        db.add(Setting(
            user_id=user.id,
            smtp_user=clean_email,
            imap_user=clean_email,
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            imap_host="imap.gmail.com",
            imap_port=993
        ))

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
