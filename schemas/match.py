from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


class MatchCreate(BaseModel):
    season_id  : int
    team_a     : str
    team_b     : str
    match_date : datetime
    venue      : Optional[str] = None

    @field_validator("team_b")
    def teams_different(cls, v, info):
        if "team_a" in info.data and v == info.data["team_a"]:
            raise ValueError("team_a and team_b must be different")
        return v


class MatchStatusUpdate(BaseModel):
    status : str  # upcoming, live, finished, cancelled


class MatchResultUpdate(BaseModel):
    winner : str


class MatchResponse(BaseModel):
    id         : int
    season_id  : int
    team_a     : str
    team_b     : str
    match_date : datetime
    venue      : Optional[str]
    status     : str
    winner     : Optional[str]
    created_at : datetime

    class Config:
        from_attributes = True
