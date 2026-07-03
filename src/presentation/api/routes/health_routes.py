from fastapi import APIRouter, Request

from ....infrastructure.config.settings import Settings

router = APIRouter(tags=["health"])


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


@router.get("/health")
async def health_check(request: Request) -> dict:
    settings = get_app_settings(request)
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/health/live")
async def live_check(request: Request) -> dict:
    settings = get_app_settings(request)
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@router.get("/health/ready")
async def readiness_check(request: Request) -> dict:
    settings = get_app_settings(request)
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "checks": {"application": "ok"},
    }
