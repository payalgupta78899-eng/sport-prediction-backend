import json
from typing import Optional, Any
from core.redis_client import get_redis
from core.config import settings


class CacheService:
    def __init__(self):
        self.r = get_redis()

    def get(self, key: str) -> Optional[Any]:
        try:
            data = self.r.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception:
            return None  # Redis down — return None, fall through to DB

    def set(self, key: str, data: Any, ttl: int) -> bool:
        try:
            self.r.setex(key, ttl, json.dumps(data, default=str))
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        try:
            self.r.delete(key)
            return True
        except Exception:
            return False

    def delete_pattern(self, pattern: str) -> bool:
        """Delete all keys matching a pattern"""
        try:
            keys = self.r.keys(pattern)
            if keys:
                self.r.delete(*keys)
            return True
        except Exception:
            return False

    # ── Leaderboard ───────────────────────────────
    def get_leaderboard(self, season_id: int) -> Optional[Any]:
        return self.get(f"leaderboard:season:{season_id}")

    def set_leaderboard(self, season_id: int, data: Any) -> bool:
        return self.set(
            f"leaderboard:season:{season_id}",
            data,
            settings.LEADERBOARD_CACHE_TTL
        )

    def bust_leaderboard(self, season_id: int) -> bool:
        return self.delete(f"leaderboard:season:{season_id}")

    def get_alltime_leaderboard(self) -> Optional[Any]:
        return self.get("leaderboard:alltime")

    def set_alltime_leaderboard(self, data: Any) -> bool:
        return self.set("leaderboard:alltime", data, settings.LEADERBOARD_CACHE_TTL)

    def bust_alltime_leaderboard(self) -> bool:
        return self.delete("leaderboard:alltime")

    # ── Match ─────────────────────────────────────
    def get_match(self, match_id: int) -> Optional[Any]:
        return self.get(f"match:{match_id}")

    def set_match(self, match_id: int, data: Any, finished: bool = False) -> bool:
        ttl = settings.MATCH_FINISHED_CACHE_TTL if finished else settings.MATCH_CACHE_TTL
        return self.set(f"match:{match_id}", data, ttl)

    def bust_match(self, match_id: int) -> bool:
        return self.delete(f"match:{match_id}")

    # ── Token Blacklist ───────────────────────────
    def blacklist_access_token(self, token: str, ttl: int) -> bool:
        try:
            self.r.setex(f"blacklist:access:{token}", ttl, "1")
            return True
        except Exception:
            return False

    def is_access_token_blacklisted(self, token: str) -> bool:
        try:
            return bool(self.r.get(f"blacklist:access:{token}"))
        except Exception:
            return False


cache_service = CacheService()
