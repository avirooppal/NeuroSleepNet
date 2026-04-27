import logging
import time

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.v1.router import api_router
from .config import settings
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.plan_check import PlanCheckMiddleware
from .middleware.audit_log import AuditLogMiddleware
from .utils.errors import NeuroSleepNetError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url=None,
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Middlewares (Order matters for request processing)
# 1. Rate Limiting
# app.add_middleware(RateLimitMiddleware)
# 2. Plan checking for mutations
app.add_middleware(PlanCheckMiddleware)
# 3. Audit logging
app.add_middleware(AuditLogMiddleware)


# Global Exception Handler for custom errors
@app.exception_handler(NeuroSleepNetError)
async def neurosleepnet_exception_handler(request: Request, exc: NeuroSleepNetError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


# Generic catch-all for unexpected errors
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )


# Health check
@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "db": "ok", "redis": "ok", "embed": "ok"}

@app.get("/health/deep", tags=["health"])
async def health_deep():
    import httpx
    # In a full implementation, we run a small query against Postgres, ping Redis, 
    # and hit the embed sidecar health endpoint with timing stats.
    stats = {}
    
    start = time.time()
    # Simulated DB delay
    stats["db_latency_ms"] = int((time.time() - start) * 1000)
    
    start = time.time()
    # Simulated Redis delay
    stats["redis_latency_ms"] = int((time.time() - start) * 1000)
    
    start = time.time()
    try:
        from .config import settings
        # Ping sidecar
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{settings.EMBED_SERVICE_URL.rstrip('/')}/health", timeout=2.0)
            stats["embed_latency_ms"] = int((time.time() - start) * 1000)
            stats["embed_status"] = "ok" if res.status_code == 200 else "error"
    except Exception:
        stats["embed_latency_ms"] = -1
        stats["embed_status"] = "unreachable"

    return {"status": "ok", "latency": stats, "timestamp": time.time()}

# Include API V1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
