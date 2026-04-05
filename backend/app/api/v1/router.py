from fastapi import APIRouter

from . import auth, memories, tasks, search, billing, sleep, dashboard

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(memories.router, prefix="/memories", tags=["memories"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(sleep.router, prefix="/sleep", tags=["sleep"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
