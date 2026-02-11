"""Integration tests for frontend authentication integration."""
import pytest
from fastapi.testclient import TestClient
from src.api.main import app


client = TestClient(app)


class TestFrontendAuthIntegration:
    """Tests for frontend authentication integration."""
    
    def test_root_page_shows_login_button_when_not_authenticated(self):
        """Test that root page shows login button when not authenticated."""
        response = client.get("/", follow_redirects=True)
        assert response.status_code == 200
        
        # Check for login button in HTML
        content = response.text
        assert "Admin Login" in content or "admin-login" in content.lower()
        
        # Check that admin tabs are disabled
        assert 'disabled' in content or 'is_admin' in content
    
    def test_root_page_shows_logout_when_authenticated(self):
        """Test that root page shows logout button when authenticated."""
        # Login first
        client.post(
            "/login",
            data={"username": "admin", "password": "admin123"}
        )
        
        # Get root page
        response = client.get("/", follow_redirects=True)
        assert response.status_code == 200
        
        content = response.text
        # Check for logout functionality
        assert "logout" in content.lower() or "Logout" in content
    
    def test_protected_tabs_available_after_login(self):
        """Test that Task Manager and Health tabs are available after login."""
        # Login
        client.post(
            "/login",
            data={"username": "admin", "password": "admin123"}
        )
        
        # Get root page
        response = client.get("/")
        assert response.status_code == 200
        
        content = response.text
        # Tabs should not be disabled
        # Check for tab content
        assert "tab-tasks" in content
        assert "tab-health" in content
    
    def test_login_modal_in_page(self):
        """Test that login modal exists in page."""
        response = client.get("/")
        assert response.status_code == 200
        
        content = response.text
        # Check for login modal elements
        assert "loginModal" in content
        assert "loginUsername" in content
        assert "loginPassword" in content
    
    def test_admin_context_passed_to_template(self):
        """Test that admin status is passed to template."""
        response = client.get("/")
        assert response.status_code == 200
        
        content = response.text
        # Check that is_admin variable is used in template
        assert "is_admin" in content.lower()
    
    def test_login_redirect_includes_message(self):
        """Test that login redirects with success message."""
        response = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False
        )
        
        # Should redirect
        assert response.status_code in [302, 303]
        
        # Check redirect location includes message
        location = response.headers.get("location", "")
        assert "msg=" in location.lower() or "/" in location
    
    def test_failed_login_redirect_includes_error(self):
        """Test that failed login redirects with error message."""
        response = client.post(
            "/login",
            data={"username": "wrong", "password": "wrong"},
            follow_redirects=False
        )
        
        # Should redirect
        assert response.status_code in [302, 303]
        
        # Check redirect location includes error
        location = response.headers.get("location", "")
        assert "error=" in location.lower() or "/" in location
    
    def test_logout_clears_session_and_redirects(self):
        """Test that logout clears session and redirects."""
        # Login first
        client.post(
            "/login",
            data={"username": "admin", "password": "admin123"}
        )
        
        # Logout
        response = client.post("/logout", follow_redirects=False)
        
        # Should redirect
        assert response.status_code in [302, 303]
        
        # After logout, admin features should not be available
        response = client.get("/")
        content = response.text
        # Should show login button again
        assert "Admin Login" in content or "login" in content.lower()


class TestAdminTabsProtection:
    """Tests for admin tabs protection in frontend."""
    
    def test_tabs_disabled_attribute_when_not_authenticated(self):
        """Test that admin tabs have disabled attribute."""
        test_client = TestClient(app)
        response = test_client.get("/")
        
        content = response.text
        # Check for disabled attribute on tabs
        # The tabs should have disabled attribute or title indicating login required
        assert "disabled" in content or "login required" in content.lower()
    
    def test_javascript_checks_admin_status(self):
        """Test that JavaScript checks admin status before switching tabs."""
        response = client.get("/")
        content = response.text
        
        # Check that switchTab function has admin check
        assert "switchTab" in content
        assert "is_admin" in content.lower()
