from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum


class MatchStatus(str, enum.Enum):
    upcoming  = "upcoming"
    live      = "live"
    finished  = "finished"
    cancelled = "cancelled"


class Match(Base):
    __tablename__ = "matches"

    id          = Column(Integer, primary_key=True, index=True)
    season_id   = Column(Integer, ForeignKey("seasons.id"), nullable=False, index=True)
    team_a      = Column(String(100), nullable=False)
    team_b      = Column(String(100), nullable=False)
    match_date  = Column(DateTime, nullable=False)
    venue       = Column(String(200), nullable=True)
    status      = Column(String(20), default=MatchStatus.upcoming, nullable=False)
    winner      = Column(String(100), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    season      = relationship("Season",     back_populates="matches")
    predictions = relationship("Prediction", back_populates="match", lazy="dynamic")
