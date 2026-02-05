"""Unit tests for API endpoints."""
import pytest
import sqlite3
import os
from api import app


@pytest.fixture
def client():
    """Create test client for Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def setup_test_db():
    """Setup test database with sample data."""
    # Create test database
    conn = sqlite3.connect("test_jobs.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            link TEXT NOT NULL UNIQUE,
            company TEXT NOT NULL
        )
    """)
    
    # Insert test data
    test_data = [
        ("Python Developer", "https://test.com/job/1", "TechCorp"),
        ("Data Engineer", "https://test.com/job/2", "DataCo"),
        ("Senior Python Engineer", "https://test.com/job/3", "StartupXYZ"),
    ]
    
    cursor.executemany(
        "INSERT INTO positions (title, link, company) VALUES (?, ?, ?)",
        test_data
    )
    
    conn.commit()
    conn.close()
    
    # Temporarily rename production db if it exists
    prod_db_exists = os.path.exists("jobs.db")
    if prod_db_exists:
        os.rename("jobs.db", "jobs_backup.db")
    
    # Rename test db to jobs.db
    os.rename("test_jobs.db", "jobs.db")
    
    yield
    
    # Cleanup: restore original db
    os.remove("jobs.db")
    if prod_db_exists:
        os.rename("jobs_backup.db", "jobs.db")


class TestAPI:
    """Test cases for API endpoints."""
    
    def test_positions_endpoint_success(self, client, setup_test_db):
        """Test successful search."""
        response = client.get('/positions?word=python')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'results' in data
        assert len(data['results']) == 2  # Python Developer and Senior Python Engineer
    
    def test_positions_endpoint_no_results(self, client, setup_test_db):
        """Test search with no results."""
        response = client.get('/positions?word=nonexistent')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['results'] == []
    
    def test_positions_endpoint_missing_parameter(self, client):
        """Test endpoint without required parameter."""
        response = client.get('/positions')
        
        assert response.status_code == 400
        data = response.get_json()
        
        assert 'error' in data
    
    def test_positions_endpoint_case_insensitive(self, client, setup_test_db):
        """Test case-insensitive search."""
        response = client.get('/positions?word=PYTHON')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data['results']) == 2
    
    def test_web_interface_get(self, client):
        """Test web interface GET request."""
        response = client.get('/')
        
        assert response.status_code == 200
        assert b'Buscar Vagas' in response.data
    
    def test_web_interface_post_success(self, client, setup_test_db):
        """Test web interface POST with search."""
        response = client.post('/', data={'word': 'python'})
        
        assert response.status_code == 200
        assert b'Python Developer' in response.data or b'job' in response.data.lower()
    
    def test_web_interface_post_empty(self, client):
        """Test web interface POST with empty search."""
        response = client.post('/', data={'word': ''})
        
        assert response.status_code == 200
        assert b'obrigat' in response.data  # "obrigatório" in error message
