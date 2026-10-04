from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum


class UserRole(str, enum.Enum):
    user      = "user"
    moderator = "moderator"
    admin     = "admin"


class User(Base):
    __tablename__ = "users"

    id           = Column(Integer, primary_key=True, index=True)
    username     = Column(String(50), unique=True, nullable=False, index=True)
    email        = Column(String(255), unique=True, nullable=False, index=True)
    password     = Column(String(255), nullable=False)
    role         = Column(String(20), default=UserRole.user, nullable=False)
    is_banned    = Column(Boolean, default=False)
    is_active    = Column(Boolean, default=True)
    # stores current refresh token hash
    # on new login old token is invalidated automatically
    refresh_token_hash = Column(String(255), nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    predictions   = relationship("Prediction",       back_populates="user",   lazy="dynamic")
    season_points = relationship("UserSeasonPoints", back_populates="user",   lazy="dynamic")
    audit_logs    = relationship("AuditLog",         back_populates="user",   lazy="dynamic")
