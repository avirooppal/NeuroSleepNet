from fastapi import APIRouter, Depends
from ...models.user import User

from . import auth, memories, projects, search, analytics, sleep, dashboard, benchmark, webhooks, health

api_router = APIRouter()

@api_router.get("/ping", tags=["health"])
async def ping(current_user: User = Depends(auth.get_current_user)):
    """SDK ping endpoint to validate API key."""
    return {"status": "ok", "user_id": str(current_user.id)}
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(memories.router, prefix="/memories", tags=["memories"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(sleep.router, prefix="/sleep", tags=["sleep"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(benchmark.router, prefix="/benchmark", tags=["benchmark"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
