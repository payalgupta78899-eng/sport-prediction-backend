from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"),   nullable=False, index=True)
    match_id         = Column(Integer, ForeignKey("matches.id"), nullable=False, index=True)
    predicted_winner = Column(String(100), nullable=False)
    is_correct       = Column(Boolean, nullable=True)  # None = not decided yet
    points_earned    = Column(Integer, default=0)
    created_at       = Column(DateTime, default=datetime.utcnow)

    user  = relationship("User",  back_populates="predictions")
    match = relationship("Match", back_populates="predictions")


class UserSeasonPoints(Base):
    __tablename__ = "user_season_points"

    id                  = Column(Integer, primary_key=True, index=True)
    user_id             = Column(Integer, ForeignKey("users.id"),   nullable=False, index=True)
    season_id           = Column(Integer, ForeignKey("seasons.id"), nullable=False, index=True)
    total_points        = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    total_predictions   = Column(Integer, default=0)
    current_streak      = Column(Integer, default=0)
    best_streak         = Column(Integer, default=0)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user   = relationship("User",   back_populates="season_points")
    season = relationship("Season", back_populates="user_points")
