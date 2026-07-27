import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from app.database import init_db
from app.routers import health, auth, settings, resume, context, templates, contacts, scrapers, queue
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

# API Routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(settings.router)
app.include_router(resume.router)
app.include_router(context.router)
app.include_router(templates.router)
app.include_router(contacts.router)
app.include_router(scrapers.router)
app.include_router(queue.router)

# Mount Frontend Static Bundle if built
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Ignore API calls
        if full_path.startswith("auth") or full_path.startswith("settings") or full_path.startswith("context") or full_path.startswith("resume") or full_path.startswith("templates") or full_path.startswith("contacts") or full_path.startswith("scrapers") or full_path.startswith("queue") or full_path.startswith("health"):
            return None
        index_file = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
