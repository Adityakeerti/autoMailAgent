from fastapi import APIRouter

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "AutoMail Multi-User Backend"}

@router.get("/ping")
async def ping_check():
    return {"status": "ok", "service": "AutoMail Multi-User Backend"}

