import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..deps import get_redis
from ..utils.errors import RateLimitError


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip rate limit for docs and options
        if request.method == "OPTIONS" or request.url.path.startswith("/docs") or request.url.path.startswith("/openapi.json"):
            return await call_next(request)

        # Get user from request state (set by Auth middleware)
        # For now, let's use IP address as a fallback if user is not yet authenticated
        user = getattr(request.state, "user", None)
        if user:
            user_id = str(user.id)
            limit = 1000 if user.plan == "paid" else 60
        else:
            user_id = request.client.host
            limit = 10  # Very strict for unauthenticated

        redis = await get_redis()
        
        # Key format: rate:{user_id}:{minute_timestamp}
        current_minute = int(time.time() // 60)
        key = f"rate:{user_id}:{current_minute}"
        
        try:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, 60)
                
            if count > limit:
                return JSONResponse(
                    status_code=429,
                    content={"error": "Rate limit exceeded", "retry_after": 60}
                )
        except Exception as e:
            # Don't block the request if Redis is down, but log it
            print(f"Rate limit Redis error: {e}")
            
        return await call_next(request)
