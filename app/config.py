import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./automail.db"
    STORAGE_BUCKET_URL: str = "local://storage"
    STORAGE_ACCESS_KEY: str = "local_key"
    STORAGE_SECRET_KEY: str = "local_secret"
    JWT_SECRET: str = "super-secret-jwt-key-change-in-production-12345"
    ENCRYPTION_KEY: str = ""

    # Google OAuth2 credentials & Redirect URI
    GOOGLE_CLIENT_ID: str = "1098492043422-dummyclientid.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET: str = "GOCSPX-dummyclientsecret"
    GOOGLE_REDIRECT_URI: str = "http://127.0.0.1:8000/auth/google/callback"

    # Shared System LinkedIn Scraping Cookie (Pool for all users)
    SHARED_LINKEDIN_COOKIE: str = ""

    # LLM Keys & Endpoints
    GROQ_API_KEY: str = ""
    LLAMA_API_KEY: str = ""
    OLLAMA_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    GEMINI_API_KEY: str = ""
    GITHUB_TOKEN: str = ""

    # Email Enrichment Keys
    APOLLO_API_KEY: str = ""

    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

if settings.STORAGE_BUCKET_URL.startswith("local://"):
    os.makedirs("./storage_data", exist_ok=True)
