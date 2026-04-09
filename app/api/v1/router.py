from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.version import router as version_router
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router

router = APIRouter()
router.include_router(admin_router)
router.include_router(auth_router)
router.include_router(health_router)
router.include_router(version_router)
