from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME:                    str  = "Fantasy Sports API"
    APP_VERSION:                 str  = "1.0.0"
    DEBUG:                       bool = False
    ENVIRONMENT:                 str  = "production"
    DATABASE_URL:                str  = "postgresql://user:pass@localhost/fantasy_db"
    REDIS_HOST:                  str  = "localhost"
    REDIS_PORT:                  int  = 6379
    SECRET_KEY:                  str  = "change-this-secret-key-in-production"
    ALGORITHM:                   str  = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int  = 15
    REFRESH_TOKEN_EXPIRE_DAYS:   int  = 7
    ALLOWED_ORIGINS:             str  = "http://localhost:3000"
    RATE_LIMIT_USER:             int  = 100
    RATE_LIMIT_MODERATOR:        int  = 500
    RATE_LIMIT_ADMIN:            int  = 1000
    RATE_LIMIT_UNAUTH:           int  = 20
    LEADERBOARD_CACHE_TTL:       int  = 60
    MATCH_CACHE_TTL:             int  = 300
    MATCH_FINISHED_CACHE_TTL:    int  = 3600

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()
