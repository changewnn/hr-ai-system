from fastapi import APIRouter

from app.core.config import get_settings


router = APIRouter(tags=["system"])


@router.get("/health", summary="Health check")
def health_check() -> dict[str, str]:
    settings = get_settings()
    return {"status": "healthy", "environment": settings.app_env}
