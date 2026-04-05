import logging
import json
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from ..deps import AsyncSessionLocal
from ..models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip audit log for read-only or auth/docs
        path = request.url.path
        if request.method in ["GET", "OPTIONS"] or any(
            path.startswith(p) for p in ["/docs", "/openapi.json", "/v1/auth", "/v1/billing"]
        ):
            return await call_next(request)

        response = await call_next(request)
        
        # Only log successful or client-error mutations
        if 200 <= response.status_code < 500:
            user = getattr(request.state, "user", None)
            if user:
                # Basic logging for all users, full audit for paid users
                # Since we don't have request body easily accessible here (already consumed),
                # we'll just log path/method. Body and detail should be logged in service/API handlers.
                
                async with AsyncSessionLocal() as session:
                    audit = AuditLog(
                        user_id=user.id,
                        action=f"{request.method} {path}",
                        ip=request.client.host,
                        metadata={
                            "status_code": response.status_code,
                            "plan": user.plan
                        }
                    )
                    session.add(audit)
                    await session.commit()
                    
        return response
