import uuid
from datetime import datetime, timezone
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import select
from ..deps import AsyncSessionLocal
from ..models.user import User
from ..models.api_key import ApiKey
from ..utils.crypto import verify_api_key
from ..config import settings

class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("Authorization")
        request.state.user = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
            async with AsyncSessionLocal() as db:
                if token.startswith("nsn_"):
                    key_prefix = token[:16]
                    stmt = (
                        select(ApiKey)
                        .where(ApiKey.is_active == True)
                        .where(ApiKey.key_prefix == key_prefix)
                    )
                    res = await db.execute(stmt)
                    candidate = res.scalar_one_or_none()

                    if candidate:
                        # Fix 1.4: Reject legacy SHA256 keys — force re-issue
                        if getattr(candidate, 'hash_version', 'v1') == 'v1':
                            from ..utils.errors import AuthenticationError
                            raise AuthenticationError(
                                "API key uses legacy hashing and must be re-issued. "
                                "Please generate a new key from your dashboard."
                            )
                        if verify_api_key(token, candidate.key_hash):
                            candidate.last_used_at = datetime.now(timezone.utc)
                            await db.commit()
                            user_stmt = select(User).where(User.id == candidate.user_id)
                            user_res = await db.execute(user_stmt)
                            request.state.user = user_res.scalar_one()

        # Fallback for anonymous access if enabled
        if not request.state.user and settings.ALLOW_ANONYMOUS_ACCESS:
             async with AsyncSessionLocal() as db:
                result = await db.execute(select(User).where(User.email == "anonymous@nsn.local"))
                request.state.user = result.scalar_one_or_none()

        return await call_next(request)
