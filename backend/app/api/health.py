from fastapi import APIRouter

from app import __version__
from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health() -> dict:
    settings = get_settings()
    return {"status": "ok", "version": __version__, "environment": settings.app_env, "ai": {"enabled": settings.openai_insights_enabled, "configured": bool(settings.openai_api_key), "model": settings.openai_model if settings.openai_api_key else None}}
