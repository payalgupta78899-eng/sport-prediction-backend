from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Season(Base):
    __tablename__ = "seasons"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    start_date  = Column(DateTime, nullable=False)
    end_date    = Column(DateTime, nullable=False)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    matches      = relationship("Match",            back_populates="season", lazy="dynamic")
    user_points  = relationship("UserSeasonPoints", back_populates="season", lazy="dynamic")
