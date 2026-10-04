from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class AuditLog(Base):
    """
    Tracks all important actions in the system.
    Required for production gambling/gaming apps.
    """
    __tablename__ = "audit_logs"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action     = Column(String(100), nullable=False, index=True)
    # examples: "user.login", "match.result_set", "user.banned"
    entity     = Column(String(50),  nullable=True)
    # examples: "user", "match", "prediction"
    entity_id  = Column(Integer,     nullable=True)
    details    = Column(Text,        nullable=True)
    # JSON string with extra info
    ip_address = Column(String(50),  nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="audit_logs")
