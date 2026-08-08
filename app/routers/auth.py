from typing import Optional
import urllib.parse
import datetime
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models import User, Setting, Template
from app.security import hash_password, verify_password, create_access_token, encrypt_secret, decrypt_secret, get_current_user
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


async def _exchange_google_code(code: str) -> dict:
    """Exchange an authorization code for Google tokens. Raises HTTPException on failure."""
    # Validate that real credentials are configured
    if "dummy" in settings.GOOGLE_CLIENT_ID or "dummy" in settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to your .env file."
        )

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(token_url, data=data)
            tokens = token_resp.json()

            if "error" in tokens:
                raise HTTPException(
                    status_code=400,
                    detail=f"Google token exchange failed: {tokens.get('error_description', tokens['error'])}"
                )

            access_token = tokens.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="Google did not return an access token.")

            # Fetch user profile
            userinfo_resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            profile = userinfo_resp.json()
            email = profile.get("email")

            if not email:
                raise HTTPException(
                    status_code=400,
                    detail="Google authentication failed: Email not returned by Google. Ensure 'email' scope is granted."
                )

            return {
                "email": email,
                "name": profile.get("name"),
                "access_token": access_token,
                "refresh_token": tokens.get("refresh_token"),
                "expires_in": tokens.get("expires_in", 3600),
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not reach Google OAuth servers: {str(e)}")


async def _refresh_google_access_token(refresh_token: str) -> dict:
    """Use a refresh token to get a new Google access token."""
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(token_url, data=data)
            tokens = resp.json()
            if "error" in tokens:
                raise HTTPException(status_code=401, detail=f"Google token refresh failed: {tokens.get('error_description', tokens['error'])}")
            return tokens
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not refresh Google token: {str(e)}")


async def get_fresh_google_access_token(user_setting: Setting) -> Optional[str]:
    """
    Returns a valid Google access token for the user.
    Refreshes automatically if the stored token is expired or about to expire.
    Returns None if no Google OAuth tokens are stored.
    """
    if not user_setting.google_refresh_token_enc:
        return None

    refresh_token = decrypt_secret(user_setting.google_refresh_token_enc)
    if not refresh_token:
        return None

    now = datetime.datetime.utcnow()
    # Refresh if token is missing or expires within 5 minutes
    needs_refresh = (
        not user_setting.google_access_token_enc
        or not user_setting.google_token_expiry
        or user_setting.google_token_expiry <= now + datetime.timedelta(minutes=5)
    )

    if not needs_refresh:
        return decrypt_secret(user_setting.google_access_token_enc)

    # Refresh the token
    try:
        new_tokens = await _refresh_google_access_token(refresh_token)
        new_access = new_tokens.get("access_token")
        expires_in = new_tokens.get("expires_in", 3600)

        user_setting.google_access_token_enc = encrypt_secret(new_access)
        user_setting.google_token_expiry = now + datetime.timedelta(seconds=expires_in)
        return new_access
    except Exception:
        return None


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserSignup, response: Response, db: AsyncSession = Depends(get_db)):
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

    st_exist = await db.execute(select(Setting).where(Setting.user_id == new_user.id))
    if not st_exist.scalar_one_or_none():
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
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 3600
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, response: Response, db: AsyncSession = Depends(get_db)):
    clean_email = credentials.email.strip().lower()
    res = await db.execute(select(User).where(User.email == clean_email))
    user = res.scalar_one_or_none()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user_id=user.id, email=user.email)
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 3600
    )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/google/url")
async def get_google_auth_url():
    """Generates official Google OAuth2 consent URL with Gmail send scope"""
    if "dummy" in settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured. Add GOOGLE_CLIENT_ID to your .env file."
        )
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        # openid + email + profile for login; gmail scope for XOAUTH2 sending
        "scope": "openid email profile https://mail.google.com/",
        "access_type": "offline",      # ensures refresh_token is returned
        "prompt": "select_account consent"  # forces account selector and re-consent to get refresh_token
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return {"url": url}


@router.get("/google/callback")
async def google_auth_callback(code: str = Query(...), db: AsyncSession = Depends(get_db)):
    """
    Handles Google OAuth2 redirect callback.
    - Exchanges auth code for access + refresh tokens
    - Creates or updates user in DB
    - Stores encrypted refresh_token for long-term XOAUTH2 sending
    - Redirects browser to dashboard with JWT
    """
    google_data = await _exchange_google_code(code)

    email = google_data["email"]
    access_token = google_data["access_token"]
    refresh_token = google_data.get("refresh_token")
    expires_in = google_data.get("expires_in", 3600)
    clean_email = email.strip().lower()

    # Find or create user
    res = await db.execute(select(User).where(User.email == clean_email))
    user = res.scalar_one_or_none()

    if not user:
        user = User(
            email=clean_email,
            # OAuth users don't have a password; set a random non-guessable hash
            password_hash=hash_password(f"google_oauth_{clean_email}_no_password_login")
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        for tmpl in DEFAULT_TEMPLATES:
            db.add(Template(
                user_id=user.id,
                category=tmpl["category"],
                subject_template=tmpl["subject_template"],
                body_template=tmpl["body_template"]
            ))

    # Upsert Gmail settings with OAuth tokens
    st_res = await db.execute(select(Setting).where(Setting.user_id == user.id))
    st = st_res.scalar_one_or_none()
    if not st:
        st = Setting(user_id=user.id)
        db.add(st)

    now = datetime.datetime.utcnow()
    st.smtp_user = clean_email
    st.smtp_host = "smtp.gmail.com"
    st.smtp_port = 587
    st.imap_user = clean_email
    st.imap_host = "imap.gmail.com"
    st.imap_port = 993

    # Always update access token
    st.google_access_token_enc = encrypt_secret(access_token)
    st.google_token_expiry = now + datetime.timedelta(seconds=expires_in)

    # Only update refresh_token if Google provided one (it's only returned on first consent)
    if refresh_token:
        st.google_refresh_token_enc = encrypt_secret(refresh_token)

    await db.commit()

    jwt_token = create_access_token(user_id=user.id, email=user.email)

    # Redirect to frontend with token as URL param (needed for cross-origin Vercel → Render setup)
    # Falls back to "/" (same-origin) when FRONTEND_URL is not configured
    frontend_base = settings.FRONTEND_URL.rstrip("/") if settings.FRONTEND_URL else ""
    redirect_url = f"{frontend_base}/?token={jwt_token}" if frontend_base else f"/?token={jwt_token}"

    response = RedirectResponse(url=redirect_url)
    response.set_cookie(
        key="token",
        value=jwt_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 3600
    )
    return response


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="token")
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}


@router.get("/google/status")
async def google_oauth_status(db: AsyncSession = Depends(get_db)):
    """Returns whether Google OAuth is properly configured server-side"""
    configured = (
        settings.GOOGLE_CLIENT_ID
        and "dummy" not in settings.GOOGLE_CLIENT_ID
        and settings.GOOGLE_CLIENT_SECRET
        and "dummy" not in settings.GOOGLE_CLIENT_SECRET
    )
    return {"configured": configured}
