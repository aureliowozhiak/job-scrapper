"""Pytest configuration and fixtures."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import tempfile
import os

from src.database.models import Base
from src.database.connection import get_db
from src.api.main import app


@pytest.fixture(scope="function")
def test_db():
    """Create a temporary test database."""
    import tempfile
    import os
    
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    
    # Ensure directory exists
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    # Create engine
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session factory
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = TestSessionLocal()
    
    yield session
    
    # Cleanup
    session.close()
    engine.dispose()
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope="function")
def client(test_db):
    """Create test client with test database."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass  # Don't close here, let test_db fixture handle it
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_position_data():
    """Sample position data for testing."""
    return {
        "title": "Senior Python Developer",
        "link": "https://example.com/job/123",
        "company": "Tech Corp"
    }


@pytest.fixture
def multiple_positions():
    """Multiple position records for testing."""
    return [
        {
            "title": "Python Developer",
            "link": "https://example.com/job/1",
            "company": "Company A"
        },
        {
            "title": "FastAPI Engineer",
            "link": "https://example.com/job/2",
            "company": "Company B"
        },
        {
            "title": "Backend Developer",
            "link": "https://example.com/job/3",
            "company": "Company C"
        }
    ]


@pytest.fixture
def authenticated_client():
    """Return a test client with admin authentication mocked."""
    from src.core.permissions import require_admin
    
    async def mock_require_admin():
        return True
    
    app.dependency_overrides[require_admin] = mock_require_admin
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

