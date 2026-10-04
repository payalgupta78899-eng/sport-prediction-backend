from sqlalchemy import (
    Column, Integer, String, Boolean,
    DateTime, ForeignKey, Text, Float, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base

# SEASON

class Season(Base):
    __tablename__ = "seasons"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), nullable=False, unique=True)
    # e.g. "IPL 2025", "IPL 2026"
    sport      = Column(String(50), default="cricket")
    start_date = Column(DateTime, nullable=False)
    end_date   = Column(DateTime, nullable=False)
    is_active  = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    matches     = relationship("Match",           back_populates="season")
    user_points = relationship("UserSeasonPoints", back_populates="season")


# MATCH
class Match(Base):
    __tablename__ = "matches"

    id         = Column(Integer, primary_key=True, index=True)
    season_id  = Column(Integer, ForeignKey("seasons.id"), nullable=False, index=True)
    team_a     = Column(String(100), nullable=False)
    team_b     = Column(String(100), nullable=False)
    venue      = Column(String(200), nullable=True)
    match_date = Column(DateTime, nullable=False)

    status     = Column(String(20), default="upcoming")
    # upcoming → live → finished → cancelled

    winner     = Column(String(100), nullable=True)
    # None = not finished yet

    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    season      = relationship("Season",     back_populates="matches")
    predictions = relationship("Prediction", back_populates="match")


# PREDICTION
class Prediction(Base):
    __tablename__ = "predictions"

    # unique constraint — one prediction per user per match
    __table_args__ = (
        UniqueConstraint("user_id", "match_id", name="uq_user_match_prediction"),
    )

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    match_id         = Column(Integer, ForeignKey("matches.id"), nullable=False, index=True)
    predicted_winner = Column(String(100), nullable=False)
    is_correct       = Column(Boolean, nullable=True)
    # None = match not finished yet
    # True = correct prediction
    # False = wrong prediction
    points_earned    = Column(Integer, default=0)
    created_at       = Column(DateTime, default=datetime.utcnow)

    user  = relationship("User",  back_populates="predictions")
    match = relationship("Match", back_populates="predictions")


# USER SEASON POINTS
# season wise point tracking
class UserSeasonPoints(Base):
    __tablename__ = "user_season_points"

    __table_args__ = (
        UniqueConstraint("user_id", "season_id", name="uq_user_season"),
    )

    id                  = Column(Integer, primary_key=True, index=True)
    user_id             = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    season_id           = Column(Integer, ForeignKey("seasons.id"), nullable=False, index=True)
    total_points        = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    total_predictions   = Column(Integer, default=0)
    current_streak      = Column(Integer, default=0)
    best_streak         = Column(Integer, default=0)
    rank                = Column(Integer, nullable=True)
    # rank updated periodically

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user   = relationship("User",   back_populates="season_points")
    season = relationship("Season", back_populates="user_points")

    @property
    def accuracy(self) -> float:
        if self.total_predictions == 0:
            return 0.0
        return round(self.correct_predictions / self.total_predictions * 100, 2)


# AUDIT LOG
# track all important actions
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=True)
    action     = Column(String(100), nullable=False)
    # e.g. "USER_BANNED", "MATCH_RESULT_UPDATED", "ROLE_CHANGED"
    details    = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")
