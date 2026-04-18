import time
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from redis.asyncio import Redis

from ...deps import get_db
from ...config import settings

router = APIRouter()

@router.get("/deep")
async def health_deep(db: AsyncSession = Depends(get_db)):
    """
    Returns latency breakdown for deep infrastructural dependencies.
    Used by dashboard to confirm systemic health.
    """
    
    # 1. Postgres Latency
    start_pg = time.perf_counter()
    pg_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        pg_status = "unhealthy"
    pg_latency = (time.perf_counter() - start_pg) * 1000
    
    # 2. Redis Latency
    start_rd = time.perf_counter()
    rd_status = "healthy"
    try:
        redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis.ping()
    except Exception:
        rd_status = "unhealthy"
    rd_latency = (time.perf_counter() - start_rd) * 1000
    
    # 3. Overall calculation
    is_healthy = pg_status == "healthy" and rd_status == "healthy"
    
    return {
        "status": "healthy" if is_healthy else "degraded",
        "services": {
            "postgres": {
                "status": pg_status,
                "latency_ms": round(pg_latency, 2)
            },
            "redis": {
                "status": rd_status,
                "latency_ms": round(rd_latency, 2)
            }
        }
    }
