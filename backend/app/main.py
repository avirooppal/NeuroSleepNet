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
app.add_middleware(RateLimitMiddleware)
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
    return {"status": "healthy", "timestamp": time.time()}


# Include API V1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
