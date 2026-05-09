"""
RateLimitMiddleware — token bucket rate limiting via Redis.

Strategy: per-user (or per-IP for unauthenticated) sliding window counter
keyed by minute epoch. Returns HTTP 429 with Retry-After on breach.

Limits:
  - Paid users:           1000 req/min
  - Free users:            100 req/min
  - Unauthenticated IPs:    10 req/min

Skipped paths: /health, /api/v1/health/deep, /docs, /openapi.json, OPTIONS
"""

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Paths that are always exempt from rate limiting
_EXEMPT_PREFIXES = ("/health", "/docs", "/openapi.json", "/redoc", "/api/v1/auth")


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Always exempt: preflight, docs, health probes
        if request.method == "OPTIONS":
            return await call_next(request)
        for prefix in _EXEMPT_PREFIXES:
            if request.url.path.startswith(prefix):
                return await call_next(request)

        # Determine identity and limit
        user = getattr(request.state, "user", None)
        if user:
            user_key = str(user.id)
            plan = getattr(user, "plan", "free")
            limit = 1000 if plan in ("pro", "paid", "enterprise") else 100
        else:
            # Unauthenticated — key by IP
            client_host = request.client.host if request.client else "unknown"
            user_key = f"ip:{client_host}"
            limit = 10

        # Use the shared Redis pool from app.state (no new connections)
        try:
            redis = request.app.state.redis
        except AttributeError:
            # Redis not initialized yet (startup race) — let request through
            return await call_next(request)

        current_minute = int(time.time() // 60)
        key = f"nsn:rate:{user_key}:{current_minute}"

        try:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, 60)

            if count > limit:
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": "60"},
                    content={
                        "error": "rate_limit_exceeded",
                        "detail": f"Rate limit of {limit} req/min exceeded.",
                        "retry_after": 60,
                    },
                )
        except Exception as exc:
            # Redis failure degrades gracefully — never block the request
            import logging
            logging.getLogger("neurosleepnet.ratelimit").warning(
                f"Rate limit Redis error (passing request through): {exc}"
            )

        return await call_next(request)
