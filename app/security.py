import base64
import os
import datetime
from typing import Optional
import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db

# Password Hasher
pwd_hash = PasswordHash((BcryptHasher(),))

def hash_password(password: str) -> str:
    return pwd_hash.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_hash.verify(plain_password, hashed_password)

# JWT Auth
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

ALGORITHM = "HS256"

def create_access_token(user_id: int, email: str, expires_delta: Optional[datetime.timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    
    to_encode = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except Exception:
        raise credentials_exception

    from app.models.all_models import User
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user

# Encryption / Decryption at rest
def _get_fernet_key() -> bytes:
    key_str = settings.ENCRYPTION_KEY or settings.JWT_SECRET
    # Ensure 32 bytes URL-safe base64 key
    key_bytes = key_str.encode()
    if len(key_bytes) < 32:
        key_bytes = key_bytes.ljust(32, b"0")
    elif len(key_bytes) > 32:
        key_bytes = key_bytes[:32]
    return base64.urlsafe_b64encode(key_bytes)

fernet = Fernet(_get_fernet_key())

def encrypt_secret(plain_text: Optional[str]) -> Optional[str]:
    if not plain_text:
        return None
    return fernet.encrypt(plain_text.encode()).decode()

def decrypt_secret(cipher_text: Optional[str]) -> Optional[str]:
    if not cipher_text:
        return None
    try:
        return fernet.decrypt(cipher_text.encode()).decode()
    except Exception:
        return None
