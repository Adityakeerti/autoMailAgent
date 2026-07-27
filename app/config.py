import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./automail.db"
    STORAGE_BUCKET_URL: str = "local://storage"
    STORAGE_ACCESS_KEY: str = "local_key"
    STORAGE_SECRET_KEY: str = "local_secret"
    JWT_SECRET: str = "super-secret-jwt-key-change-in-production-12345"
    ENCRYPTION_KEY: str = ""

    # Google OAuth credentials
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Shared System LinkedIn Scraping Cookie (Pool for all users)
    SHARED_LINKEDIN_COOKIE: str = ""

    # LLM Keys
    GROQ_API_KEY: str = ""
    OLLAMA_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GITHUB_TOKEN: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Ensure storage dir exists if using local storage
if settings.STORAGE_BUCKET_URL.startswith("local://"):
    os.makedirs("./storage_data", exist_ok=True)
