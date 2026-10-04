from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import QueuePool
from core.config import settings

# ENGINE — connection pool

engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,           # keep 10 connections open
    max_overflow=20,        # allow 20 extra under load
    pool_timeout=30,        # wait max 30s for connection
    pool_recycle=1800,      # recycle connections every 30min
    pool_pre_ping=True,     # verify connection before use
    echo=settings.DEBUG     # log SQL in debug mode only
)

# SESSION FACTORY
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

# BASE CLASS FOR MODELS
class Base(DeclarativeBase):
    pass

# DEPENDENCY — one session per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
