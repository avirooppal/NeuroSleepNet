"""
Health check API — deep liveness probe with latency breakdown.

Fix 12: Uses request.app.state.redis (shared pool from main.py lifespan)
instead of creating a new Redis connection on every call.
"""
import time
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ...deps import get_db
from ...config import settings

router = APIRouter()


@router.get("/deep")
async def health_deep(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns latency breakdown for deep infrastructural dependencies.
    Used by the dashboard to confirm systemic health.

    Fix 12: Redis connection now comes from app.state.redis (shared pool),
    not Redis.from_url() which created a new connection per call.
    """

    # 1. Postgres Latency
    start_pg = time.perf_counter()
    pg_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        pg_status = f"unhealthy: {str(exc)[:80]}"
    pg_latency = (time.perf_counter() - start_pg) * 1000

    # 2. Redis Latency — Fix 12: use shared pool, never create a new connection here
    start_rd = time.perf_counter()
    rd_status = "healthy"
    try:
        redis = request.app.state.redis  # shared pool from lifespan
        await redis.ping()
    except AttributeError:
        rd_status = "unavailable: app.state.redis not initialised"
    except Exception as exc:
        rd_status = f"unhealthy: {str(exc)[:80]}"
    rd_latency = (time.perf_counter() - start_rd) * 1000

    # 3. Overall status
    is_healthy = pg_status == "healthy" and rd_status == "healthy"

    return {
        "status": "healthy" if is_healthy else "degraded",
        "services": {
            "postgres": {
                "status": pg_status,
                "latency_ms": round(pg_latency, 2),
            },
            "redis": {
                "status": rd_status,
                "latency_ms": round(rd_latency, 2),
            },
        },
    }
