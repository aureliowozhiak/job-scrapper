"""Database connection and session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from pathlib import Path
from src.core.config import settings
from src.database.models import Base


# Create engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    poolclass=StaticPool if "sqlite" in settings.database_url else None,
    echo=settings.debug
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    # Ensure database directory exists
    db_path = settings.database_url.replace("sqlite:///", "").replace("sqlite://", "")
    if db_path.startswith("./"):
        db_path = db_path[2:]
    
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_context():
    """Context manager for database sessions."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db():
    """Dependency for FastAPI to inject database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
