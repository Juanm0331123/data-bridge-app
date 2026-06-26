from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.modules.sync.router import router as sync_router

router = APIRouter()

router.include_router(
    health_router,
    prefix="/health",
    tags=["Health"],
)

router.include_router(
    sync_router,
    prefix="/sync",
    tags=["Sync"],
)
