from fastapi import Request
from fastapi.responses import JSONResponse
from core.redis_client import get_redis
from core.security import decode_token
from core.config import settings
import time


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware.
    Different limits per role.
    Resets every minute.
    Uses Redis INCR — atomic, no race conditions.
    """
    # skip rate limiting for public/health routes
    skip_routes = [
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/"
    ]
    if request.url.path in skip_routes:
        return await call_next(request)

    # determine identity and limit
    token = request.headers.get("Authorization", "").replace("Bearer ", "")

    if token:
        payload = decode_token(token)
        if payload:
            identity = f"user:{payload.get('sub', 'unknown')}"
            role     = payload.get("role", "user")
            if role == "admin":
                limit = settings.RATE_LIMIT_ADMIN
            elif role == "moderator":
                limit = settings.RATE_LIMIT_MODERATOR
            else:
                limit = settings.RATE_LIMIT_USER
        else:
            identity = f"ip:{request.client.host}"
            limit    = settings.RATE_LIMIT_UNAUTH
    else:
        identity = f"ip:{request.client.host}"
        limit    = settings.RATE_LIMIT_UNAUTH

    # redis key includes current minute — auto resets
    current_minute = int(time.time() // 60)
    redis_key      = f"ratelimit:{identity}:{current_minute}"

    try:
        r     = get_redis()
        count = r.incr(redis_key)    # atomic increment
        if count == 1:
            r.expire(redis_key, 120) # auto cleanup after 2 minutes
    except Exception:
        # Redis down — allow request through (fail open)
        return await call_next(request)

    if count > limit:
        return JSONResponse(
            status_code = 429,
            content     = {
                "detail"       : f"Rate limit exceeded. Max {limit} requests/minute.",
                "retry_after"  : "60 seconds"
            },
            headers = {
                "X-RateLimit-Limit"     : str(limit),
                "X-RateLimit-Remaining" : "0",
                "Retry-After"           : "60"
            }
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"]     = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
    return response
