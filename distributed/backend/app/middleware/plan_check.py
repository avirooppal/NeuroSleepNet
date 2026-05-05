from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..deps import get_db
from ..services.usage_service import check_and_inc_usage
from ..utils.errors import PlanLimitError


class PlanCheckMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip plan check for non-mutating or auth/billing/docs
        path = request.url.path
        if request.method in ["GET", "OPTIONS"] or any(
            path.startswith(p) for p in ["/docs", "/openapi.json", "/v1/auth", "/v1/billing"]
        ):
            return await call_next(request)

        # Get user from request state
        user = getattr(request.state, "user", None)
        if not user:
            # Should already be authenticated by Auth middleware
            return await call_next(request)

        # Enforce limits for specific mutating operations
        # (Actually, usage decrementing/incrementing is handled in service layer, 
        # so this is just a pre-check if needed).
        # We'll rely on service layer check_and_inc_usage for accurate enforcement.
        
        return await call_next(request)
