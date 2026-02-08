"""Unit tests for Position repository."""
import pytest
from src.database.repositories import PositionRepository


def test_create_position(test_db, sample_position_data):
    """Test creating a new position."""
    repo = PositionRepository(test_db)
    position = repo.create(**sample_position_data)
    
    assert position.id is not None
    assert position.title == sample_position_data["title"]
    assert position.link == sample_position_data["link"]
    assert position.company == sample_position_data["company"]
    assert position.created_at is not None
    assert position.updated_at is not None


def test_get_by_id(test_db, sample_position_data):
    """Test retrieving position by ID."""
    repo = PositionRepository(test_db)
    created = repo.create(**sample_position_data)
    
    retrieved = repo.get_by_id(created.id)
    
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.title == created.title


def test_get_by_link(test_db, sample_position_data):
    """Test retrieving position by link."""
    repo = PositionRepository(test_db)
    created = repo.create(**sample_position_data)
    
    retrieved = repo.get_by_link(sample_position_data["link"])
    
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.link == sample_position_data["link"]


def test_upsert_new_position(test_db, sample_position_data):
    """Test upserting a new position."""
    repo = PositionRepository(test_db)
    position = repo.upsert(**sample_position_data)
    
    assert position.id is not None
    assert position.title == sample_position_data["title"]


def test_upsert_existing_position(test_db, sample_position_data):
    """Test upserting an existing position updates it."""
    repo = PositionRepository(test_db)
    
    # Create initial
    original = repo.create(**sample_position_data)
    original_id = original.id
    original_created_at = original.created_at
    
    # Upsert with updated data
    updated_data = sample_position_data.copy()
    updated_data["title"] = "Updated Title"
    updated = repo.upsert(**updated_data)
    
    assert updated.id == original_id  # Same record
    assert updated.title == "Updated Title"  # Updated
    assert updated.created_at == original_created_at  # Created date unchanged
    assert updated.updated_at > original_created_at  # Updated date changed


def test_search(test_db, multiple_positions):
    """Test searching positions by query."""
    repo = PositionRepository(test_db)
    
    # Create multiple positions
    for pos_data in multiple_positions:
        repo.create(**pos_data)
    
    # Search for "Python"
    results = repo.search("Python")
    assert len(results) == 1
    assert "Python" in results[0].title
    
    # Search for "Developer"
    results = repo.search("Developer")
    assert len(results) == 2


def test_get_all_with_filters(test_db, multiple_positions):
    """Test getting all positions with filters."""
    repo = PositionRepository(test_db)
    
    for pos_data in multiple_positions:
        repo.create(**pos_data)
    
    # Get all
    all_positions = repo.get_all()
    assert len(all_positions) == 3
    
    # Filter by company
    company_filtered = repo.get_all(company="Company A")
    assert len(company_filtered) == 1
    assert company_filtered[0].company == "Company A"
    
    # Search filter
    search_filtered = repo.get_all(search="FastAPI")
    assert len(search_filtered) == 1


def test_get_all_pagination(test_db, multiple_positions):
    """Test pagination in get_all."""
    repo = PositionRepository(test_db)
    
    for pos_data in multiple_positions:
        repo.create(**pos_data)
    
    # First page
    page1 = repo.get_all(limit=2, offset=0)
    assert len(page1) == 2
    
    # Second page
    page2 = repo.get_all(limit=2, offset=2)
    assert len(page2) == 1


def test_count(test_db, multiple_positions):
    """Test count function."""
    repo = PositionRepository(test_db)
    
    for pos_data in multiple_positions:
        repo.create(**pos_data)
    
    total = repo.count()
    assert total == 3
    
    # Count with filter
    filtered_count = repo.count(search="Python")
    assert filtered_count == 1


def test_get_stats(test_db, multiple_positions):
    """Test getting database statistics."""
    repo = PositionRepository(test_db)
    
    for pos_data in multiple_positions:
        repo.create(**pos_data)
    
    stats = repo.get_stats()
    
    assert stats["total_jobs"] == 3
    assert stats["total_companies"] == 3  # All different companies


def test_delete_by_link(test_db, sample_position_data):
    """Test deleting position by link."""
    repo = PositionRepository(test_db)
    
    repo.create(**sample_position_data)
    
    # Delete
    result = repo.delete_by_link(sample_position_data["link"])
    assert result is True
    
    # Verify deleted
    position = repo.get_by_link(sample_position_data["link"])
    assert position is None
    
    # Try deleting non-existent
    result = repo.delete_by_link("non-existent-link")
    assert result is False


def test_bulk_upsert(test_db, multiple_positions):
    """Test bulk upsert operation."""
    repo = PositionRepository(test_db)
    
    # Bulk insert
    stats = repo.bulk_upsert(multiple_positions)
    
    assert stats["inserted"] == 3
    assert stats["updated"] == 0
    assert stats["errors"] == 0
    
    # Modify and bulk upsert again
    for pos in multiple_positions:
        pos["title"] = "Updated " + pos["title"]
    
    stats = repo.bulk_upsert(multiple_positions)
    
    assert stats["inserted"] == 0
    assert stats["updated"] == 3
    assert stats["errors"] == 0




def test_bulk_upsert_with_invalid_data(test_db):
    """Test bulk upsert handles errors gracefully."""
    repo = PositionRepository(test_db)
    
    invalid_data = [
        {"title": "", "link": "", "company": ""},  # Empty fields
        {"title": "Valid", "link": "http://example.com", "company": "Company"}
    ]
    
    stats = repo.bulk_upsert(invalid_data)
    
    assert stats["inserted"] == 1
    assert stats["errors"] == 1
