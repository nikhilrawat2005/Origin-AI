"""
SQLAlchemy engine + session management.

Single place that turns DATABASE_URL into an engine/session factory.
Models import Base from here; routes/services will import get_db (added
when routes are wired in Stage 4+).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# SQLite needs this connect_arg when used with FastAPI's threaded requests.
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Called at app startup (Stage 4+) and in tests."""
    Base.metadata.create_all(bind=engine)
