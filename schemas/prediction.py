from pydantic import BaseModel
from datetime import datetime
from typing import Optional


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


class LeaderboardEntry(BaseModel):
    rank                : int
    username            : str
    total_points        : int
    correct_predictions : int
    total_predictions   : int
    accuracy            : float
    current_streak      : int
    best_streak         : int


class MyStatsResponse(BaseModel):
    season              : str
    total_points        : int
    correct_predictions : int
    total_predictions   : int
    accuracy            : float
    current_streak      : int
    best_streak         : int
    rank                : Optional[int]
