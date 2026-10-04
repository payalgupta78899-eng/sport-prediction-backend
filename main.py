from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from database import engine
from models import user, season, match, prediction, audit  # import all models
from database import Base

from middleware.rate_limit import rate_limit_middleware
from middleware.logging   import logging_middleware

from routers import auth, seasons, matches, predictions, leaderboard, admin

# create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title       = settings.APP_NAME,
    version     = settings.APP_VERSION,
    description = """
## Fantasy Sports Prediction Game API

A production-ready backend for a fantasy sports prediction platform.

### Features
- **JWT Authentication** with httpOnly refresh token rotation
- **RBAC** — user, moderator, admin roles
- **Season-based points** — fresh competition every season
- **Streak bonuses** — reward consecutive correct predictions
- **Redis caching** — leaderboard and match caching
- **Rate limiting** — per role, per minute
- **Audit logging** — full action trail
- **ACID transactions** — safe point awarding

### Roles
| Role | Permissions |
|------|------------|
| user | predict matches, view leaderboard |
| moderator | manage matches, set results |
| admin | manage users, seasons, view audit logs |
    """,
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

# MIDDLEWARE — order matters, added in reverse execution order

# 1. CORS — must be first
app.add_middleware(
    CORSMiddleware,
    allow_origins     = settings.allowed_origins_list,
    allow_credentials = True,
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers     = ["Authorization", "Content-Type", "Accept"],
)

# 2. Logging
app.middleware("http")(logging_middleware)

# 3. Rate limiting
app.middleware("http")(rate_limit_middleware)

# GLOBAL EXCEPTION HANDLER

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code = 500,
        content     = {"detail": "Internal server error"}
    )
# ROUTERS

API_PREFIX = "/api/v1"

app.include_router(auth.router,         prefix=API_PREFIX)
app.include_router(seasons.router,      prefix=API_PREFIX)
app.include_router(matches.router,      prefix=API_PREFIX)
app.include_router(predictions.router,  prefix=API_PREFIX)
app.include_router(leaderboard.router,  prefix=API_PREFIX)
app.include_router(admin.router,        prefix=API_PREFIX)

# HEALTH CHECK

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status"     : "healthy",
        "app"        : settings.APP_NAME,
        "version"    : settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }

@app.get("/", tags=["Health"])
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs"   : "/docs",
        "version": settings.APP_VERSION
    }
