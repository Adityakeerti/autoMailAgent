from fastapi import FastAPI
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

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(settings.router)
app.include_router(resume.router)
app.include_router(context.router)
app.include_router(templates.router)
app.include_router(contacts.router)
app.include_router(scrapers.router)
app.include_router(queue.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
