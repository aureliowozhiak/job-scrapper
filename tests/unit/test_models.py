"""Unit tests for database models."""
import pytest
from datetime import datetime, timezone
from src.database.models import Position


class TestPositionModel:
    """Test Position model."""
    
    def test_position_creation(self):
        """Test creating a Position instance."""
        position = Position(
            title="Python Developer",
            link="https://example.com/job/1",
            company="TechCorp"
        )
        
        assert position.title == "Python Developer"
        assert position.link == "https://example.com/job/1"
        assert position.company == "TechCorp"
    
    def test_position_repr(self):
        """Test Position __repr__ method."""
        position = Position(
            id=1,
            title="Data Engineer",
            link="https://example.com/job/2",
            company="DataCo"
        )
        
        repr_str = repr(position)
        assert "Position" in repr_str
        assert "id=1" in repr_str
        assert "Data Engineer" in repr_str
        assert "DataCo" in repr_str
    
    def test_position_to_dict(self):
        """Test Position to_dict method."""
        now = datetime.now(timezone.utc)
        position = Position(
            id=1,
            title="Backend Developer",
            link="https://example.com/job/3",
            company="StartupXYZ",
            created_at=now,
            updated_at=now
        )
        
        result = position.to_dict()
        
        assert result["id"] == 1
        assert result["title"] == "Backend Developer"
        assert result["link"] == "https://example.com/job/3"
        assert result["company"] == "StartupXYZ"
        assert result["created_at"] is not None
        assert result["updated_at"] is not None
    
    def test_position_to_dict_no_timestamps(self):
        """Test to_dict with None timestamps."""
        position = Position(
            id=2,
            title="Frontend Developer",
            link="https://example.com/job/4",
            company="WebCo",
            created_at=None,
            updated_at=None
        )
        
        result = position.to_dict()
        
        assert result["created_at"] is None
        assert result["updated_at"] is None
    
    def test_position_tablename(self):
        """Test Position table name."""
        assert Position.__tablename__ == "positions"
    
    def test_position_columns(self):
        """Test Position has required columns."""
        assert hasattr(Position, 'id')
        assert hasattr(Position, 'title')
        assert hasattr(Position, 'link')
        assert hasattr(Position, 'company')
        assert hasattr(Position, 'created_at')
        assert hasattr(Position, 'updated_at')
