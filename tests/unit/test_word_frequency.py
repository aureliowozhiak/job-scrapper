"""Tests for word frequency analysis endpoint."""
import pytest
from datetime import datetime, timezone
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
        
        sources = ["SkipTheDrive", "RemoteOK", "SkipTheDrive", "RemoteOK", "Remotive",
                   "SkipTheDrive", "RemoteOK", "Remotive", "SkipTheDrive", "RemoteOK"]
        
        for i, title in enumerate(titles):
            pos = MagicMock(spec=Position)
            pos.id = i + 1
            pos.title = title
            pos.link = f"https://example.com/job/{i+1}"
            pos.company = f"Company {i+1}"
            pos.source = sources[i]
            pos.created_at = datetime(2026, 2, 10 if i < 5 else 9, 12, 0, 0, tzinfo=timezone.utc)
            positions.append(pos)
        
        return positions
    
    def test_word_frequency_success(self, mock_positions):
        """Test word frequency analysis with data."""
        from unittest.mock import patch
        
        # Create mock session
        mock_session = MagicMock(spec=Session)
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.all.return_value = mock_positions
        
        # Mock repository count() to return realistic values
        with patch('src.api.routes.jobs.PositionRepository') as MockRepo:
            mock_repo_instance = MockRepo.return_value
            
            # Mock count() to return number of matching positions
            def mock_count(search=None, **kwargs):
                if search:
                    search_lower = search.lower()
                    count = sum(1 for p in mock_positions if search_lower in p.title.lower())
                    return count
                return len(mock_positions)
            
            mock_repo_instance.count.side_effect = mock_count
            
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
                assert all("text" in item and "count" in item for item in data["single_words"])
                
                # Python should be most frequent
                words = {item["text"]: item["count"] for item in data["single_words"]}
                assert "python" in words
                assert words["python"] > 5  # Appears in most titles
                
                # Check two-word phrases
                assert len(data["two_word_phrases"]) > 0
                assert all("text" in item and "count" in item for item in data["two_word_phrases"])
                
                # Check three-word phrases (might be empty with limited test data)
                assert isinstance(data["three_word_phrases"], list)
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

    def test_word_frequency_with_ngram_filter(self, mock_positions):
        """Test word frequency with n-gram type filter."""
        from unittest.mock import patch
        
        mock_session = MagicMock(spec=Session)
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_positions
        mock_query.count.return_value = 5
        
        def override_get_db():
            return mock_session
        
        app.dependency_overrides[get_db] = override_get_db
        
        try:
            client = TestClient(app)
            
            # Test single words only
            response = client.get("/api/jobs/analysis/word-frequency?ngram_type=1&top_n=5")
            assert response.status_code == 200
            data = response.json()
            assert len(data["single_words"]) > 0
            assert len(data["two_word_phrases"]) == 0
            assert len(data["three_word_phrases"]) == 0
            
            # Test two-word phrases only
            response = client.get("/api/jobs/analysis/word-frequency?ngram_type=2&top_n=5")
            assert response.status_code == 200
            data = response.json()
            assert len(data["single_words"]) == 0
            assert len(data["two_word_phrases"]) > 0
            assert len(data["three_word_phrases"]) == 0
            
            # Test three-word phrases only
            response = client.get("/api/jobs/analysis/word-frequency?ngram_type=3&top_n=5")
            assert response.status_code == 200
            data = response.json()
            assert len(data["single_words"]) == 0
            assert len(data["two_word_phrases"]) == 0
            # three_word_phrases might be empty depending on data
            
        finally:
            app.dependency_overrides.clear()
    
    def test_word_frequency_with_source_filter(self, mock_positions):
        """Test word frequency with source filter."""
        mock_session = MagicMock(spec=Session)
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # Filter to only SkipTheDrive positions
        skip_positions = [p for p in mock_positions if p.source == "SkipTheDrive"]
        mock_query.all.return_value = skip_positions
        mock_query.count.return_value = len(skip_positions)
        
        def override_get_db():
            return mock_session
        
        app.dependency_overrides[get_db] = override_get_db
        
        try:
            client = TestClient(app)
            response = client.get("/api/jobs/analysis/word-frequency?source=SkipTheDrive&top_n=5")
            
            assert response.status_code == 200
            data = response.json()
            
            # Should have results
            assert "single_words" in data
            assert isinstance(data["single_words"], list)
            
        finally:
            app.dependency_overrides.clear()
    
    def test_word_frequency_with_date_filter(self, mock_positions):
        """Test word frequency with date filter."""
        mock_session = MagicMock(spec=Session)
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # Filter to only Feb 10 positions (first 5)
        feb10_positions = mock_positions[:5]
        mock_query.all.return_value = feb10_positions
        mock_query.count.return_value = len(feb10_positions)
        
        def override_get_db():
            return mock_session
        
        app.dependency_overrides[get_db] = override_get_db
        
        try:
            client = TestClient(app)
            response = client.get("/api/jobs/analysis/word-frequency?date_from=2026-02-10&top_n=5")
            
            assert response.status_code == 200
            data = response.json()
            
            # Should have results
            assert "single_words" in data
            assert isinstance(data["single_words"], list)
            
        finally:
            app.dependency_overrides.clear()
    
    def test_word_frequency_with_compound_filters(self, mock_positions):
        """Test word frequency with multiple filters combined."""
        mock_session = MagicMock(spec=Session)
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # Filter to SkipTheDrive positions from Feb 10
        filtered = [p for p in mock_positions[:5] if p.source == "SkipTheDrive"]
        mock_query.all.return_value = filtered
        mock_query.count.return_value = len(filtered)
        
        def override_get_db():
            return mock_session
        
        app.dependency_overrides[get_db] = override_get_db
        
        try:
            client = TestClient(app)
            response = client.get(
                "/api/jobs/analysis/word-frequency"
                "?source=SkipTheDrive&date_from=2026-02-10&ngram_type=1&top_n=5"
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should have single words only
            assert len(data["single_words"]) > 0
            assert len(data["two_word_phrases"]) == 0
            assert len(data["three_word_phrases"]) == 0
            
        finally:
            app.dependency_overrides.clear()

