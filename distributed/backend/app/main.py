import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .api.v1.router import api_router
from .config import settings
from .deps import get_db
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.plan_check import PlanCheckMiddleware
from .middleware.audit_log import AuditLogMiddleware
from .middleware.auth import AuthenticationMiddleware
from .utils.errors import NeuroSleepNetError

# Fix 5.1: Avoid global logging configuration; set specific logger levels
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ── App lifespan — shared Redis pool ─────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown: create and destroy shared Redis pool."""
    # Fix 2.1: Validate encryption key before accepting traffic
    settings.validate_encryption_key()

    # Fix 1.6: Warn if anonymous access is enabled
    if settings.ALLOW_ANONYMOUS_ACCESS:
        logger.warning(
            "[NSN] ALLOW_ANONYMOUS_ACCESS is enabled. "
            "Anonymous users will be granted free-tier access. "
            "Disable this in production."
        )
    app.state.redis = Redis.from_url(
        str(settings.REDIS_URL),
        encoding="utf-8",
        decode_responses=True,
    )
    logger.info("[NSN] Redis pool initialised.")
    yield
    await app.state.redis.aclose()
    logger.info("[NSN] Redis pool closed.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

# ── CORS — Fix 5: env-configurable origins, not wildcard ─────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Project-ID", "Idempotency-Key"],
)

# ── Custom Middlewares ────────────────────────────────────────────────────────
# Fix 1: RateLimitMiddleware re-enabled (uses app.state.redis — no new connections)
# Order: Auth (runs first) -> Audit -> Plan -> Rate (runs last)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(PlanCheckMiddleware)
app.add_middleware(AuditLogMiddleware)
app.add_middleware(AuthenticationMiddleware)


# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(NeuroSleepNetError)
async def neurosleepnet_exception_handler(request: Request, exc: NeuroSleepNetError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )


# ── Fix 6: /health with real DB + Redis liveness checks ──────────────────────

@app.get("/health")
async def health():
    """Simple liveness probe — always returns 200."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/health/deep")
async def health_deep(request: Request):
    """
    Deep health check: validates DB and Redis connectivity.
    Returns 503 if any critical service is down.
    """
    checks = {}
    overall = "ok"

    # Database — use shared session from deps
    try:
        async for db in get_db():
            await db.execute("SELECT 1")
            checks["db"] = "ok"
            break
    except Exception as exc:
        checks["db"] = f"error: {str(exc)[:80]}"
        overall = "degraded"

    # Redis — use shared pool, never create a new connection here
    try:
        redis = request.app.state.redis
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {str(exc)[:80]}"
        overall = "degraded"
    
    # Fix 5.2: Add embedding service health check
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.EMBED_SERVICE_URL}/health")
            if resp.status_code == 200:
                checks["embed"] = "ok"
            else:
                checks["embed"] = f"error: HTTP {resp.status_code}"
                overall = "degraded"
    except Exception as exc:
        checks["embed"] = f"error: {str(exc)[:80]}"
        overall = "degraded"

    http_status = 200 if overall == "ok" else 503
    return JSONResponse(
        status_code=http_status,
        content={
            "status": overall,
            "version": settings.VERSION,
            **checks,
        },
    )


# ── API routers ───────────────────────────────────────────────────────────────

app.include_router(api_router, prefix=settings.API_V1_STR)

# SDK Dashboard Parity endpoints (/api/stats etc.)
from .api.parity import parity_router
app.include_router(parity_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
