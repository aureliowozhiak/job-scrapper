"""Tests for word frequency analysis endpoint."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from sqlalchemy.orm import Session
from src.api.main import app
from src.database.models import Position
from src.database.connection import get_db


class TestWordFrequencyEndpoint:
    """Tests for /api/jobs/analysis/word-frequency endpoint."""
    
    @pytest.fixture
    def mock_positions(self):
        """Create mock positions for testing."""
        positions = []
        
        # Create mock position objects with various titles
        titles = [
            "Senior Python Developer",
            "Python Developer",
            "Python Engineer",
            "Senior Data Engineer Python",
            "Full Stack Developer Python React",
            "Backend Developer with Python",
            "Machine Learning Engineer",
            "Senior Machine Learning Engineer",
            "Data Scientist Python",
            "Python Django Developer",
        ]
        
        for i, title in enumerate(titles):
            pos = MagicMock(spec=Position)
            pos.id = i + 1
            pos.title = title
            pos.link = f"https://example.com/job/{i+1}"
            pos.company = f"Company {i+1}"
            pos.source = "test"
            positions.append(pos)
        
        return positions
    
    def test_word_frequency_success(self, mock_positions):
        """Test word frequency analysis with data."""
        # Create mock session
        mock_session = MagicMock(spec=Session)
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.all.return_value = mock_positions
        
        # Override dependency
        def override_get_db():
            return mock_session
        
        app.dependency_overrides[get_db] = override_get_db
        
        try:
            client = TestClient(app)
            response = client.get("/api/jobs/analysis/word-frequency?top_n=10")
            
            assert response.status_code == 200
            data = response.json()
            
            # Check structure
            assert "single_words" in data
            assert "two_word_phrases" in data
            assert "three_word_phrases" in data
            
            # Check single words
            assert len(data["single_words"]) > 0
            assert all("word" in item and "count" in item for item in data["single_words"])
            
            # Python should be most frequent
            words = {item["word"]: item["count"] for item in data["single_words"]}
            assert "python" in words
            assert words["python"] > 5  # Appears in most titles
            
            # Check two-word phrases
            assert len(data["two_word_phrases"]) > 0
            assert all("phrase" in item and "count" in item for item in data["two_word_phrases"])
            
            # Check three-word phrases
            assert len(data["three_word_phrases"]) > 0
            assert all("phrase" in item and "count" in item for item in data["three_word_phrases"])
        finally:
            app.dependency_overrides.clear()
    
    def test_word_frequency_empty_database(self):
        """Test word frequency with empty database."""
        # Create mock session with no data
        mock_session = MagicMock(spec=Session)
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.all.return_value = []
        
        # Override dependency
        def override_get_db():
            return mock_session
        
        app.dependency_overrides[get_db] = override_get_db
        
        try:
            client = TestClient(app)
            response = client.get("/api/jobs/analysis/word-frequency")
            
            assert response.status_code == 200
            data = response.json()
            
            # All lists should be empty
            assert data["single_words"] == []
            assert data["two_word_phrases"] == []
            assert data["three_word_phrases"] == []
        finally:
            app.dependency_overrides.clear()

