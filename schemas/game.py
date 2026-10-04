from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


# ─────────────────────────────────────
# SEASON SCHEMAS
# ─────────────────────────────────────
class SeasonCreate(BaseModel):
    name       : str
    sport      : str = "cricket"
    start_date : datetime
    end_date   : datetime

    @field_validator("name")
    def name_valid(cls, v):
        if len(v) < 3:
            raise ValueError("Season name too short")
        return v


class SeasonResponse(BaseModel):
    id         : int
    name       : str
    sport      : str
    start_date : datetime
    end_date   : datetime
    is_active  : bool
    created_at : datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────
# MATCH SCHEMAS
# ─────────────────────────────────────
class MatchCreate(BaseModel):
    season_id  : int
    team_a     : str
    team_b     : str
    venue      : Optional[str] = None
    match_date : datetime

    @field_validator("team_b")
    def teams_different(cls, v, info):
        if "team_a" in info.data and v == info.data["team_a"]:
            raise ValueError("Team A and Team B cannot be same")
        return v


class MatchResponse(BaseModel):
    id         : int
    season_id  : int
    team_a     : str
    team_b     : str
    venue      : Optional[str]
    match_date : datetime
    status     : str
    winner     : Optional[str]
    created_at : datetime

    class Config:
        from_attributes = True


class MatchResultUpdate(BaseModel):
    winner : str


class MatchStatusUpdate(BaseModel):
    status : str

    @field_validator("status")
    def status_valid(cls, v):
        allowed = ["upcoming", "live", "finished", "cancelled"]
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v


# ─────────────────────────────────────
# PREDICTION SCHEMAS
# ─────────────────────────────────────
class PredictionCreate(BaseModel):
    match_id         : int
    predicted_winner : str


class PredictionResponse(BaseModel):
    id               : int
    match_id         : int
    predicted_winner : str
    is_correct       : Optional[bool]
    points_earned    : int
    created_at       : datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────
# LEADERBOARD SCHEMAS
# ─────────────────────────────────────
class LeaderboardEntry(BaseModel):
    rank                : int
    username            : str
    total_points        : int
    correct_predictions : int
    total_predictions   : int
    accuracy            : float
    current_streak      : int
    best_streak         : int


class LeaderboardResponse(BaseModel):
    season_id   : int
    season_name : str
    entries     : List[LeaderboardEntry]
    total_users : int
    source      : str = "db"


# ─────────────────────────────────────
# USER STATS SCHEMAS
# ─────────────────────────────────────
class UserStatsResponse(BaseModel):
    season_name         : str
    total_points        : int
    correct_predictions : int
    total_predictions   : int
    accuracy            : float
    current_streak      : int
    best_streak         : int
    rank                : Optional[int]


# ─────────────────────────────────────
# ADMIN SCHEMAS
# ─────────────────────────────────────
class BanUserRequest(BaseModel):
    reason : str


class ChangeRoleRequest(BaseModel):
    role : str

    @field_validator("role")
    def role_valid(cls, v):
        if v not in ["user", "moderator", "admin"]:
            raise ValueError("Role must be user, moderator or admin")
        return v


class AdminUserResponse(BaseModel):
    id         : int
    username   : str
    email      : str
    role       : str
    is_active  : bool
    is_banned  : bool
    ban_reason : Optional[str]
    created_at : datetime
    last_login : Optional[datetime]

    class Config:
        from_attributes = True
