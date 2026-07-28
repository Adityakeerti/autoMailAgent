import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.routers import health, auth, settings as routers_settings, resume, context, templates, contacts, scrapers, queue
from app.workers.scheduler import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables on startup
    await init_db()
    # Start background scheduler
    start_scheduler()
    yield
    # Stop scheduler on shutdown
    stop_scheduler()

app = FastAPI(
    title="AutoMail Multi-User Cold Mail Engine",
    description="Automated cold outreach engine with multi-user isolation, resume-driven context, and multi-fallback LLM personalizer",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for Vercel Frontend and Local Development (Handles pre-flight OPTIONS requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(routers_settings.router)
app.include_router(resume.router)
app.include_router(context.router)
app.include_router(templates.router)
app.include_router(contacts.router)
app.include_router(scrapers.router)
app.include_router(queue.router)

# Mount Frontend Assets & Serve SPA Index (only when built dist is present — local/mono-repo)
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
assets_dir = os.path.join(frontend_dist, "assets")

if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# Always register the catch-all GET route.
# On Render (API-only), this returns a JSON status.
# On local mono-repo with built dist, it serves the SPA index.
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    index_file = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"status": "ok", "service": "AutoMail API", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)
