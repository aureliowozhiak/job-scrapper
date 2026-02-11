"""Unit tests for permission dependencies."""
import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import HTTPException, status
from src.core.permissions import require_admin, get_optional_admin
from src.core.config import settings


class TestRequireAdmin:
    """Tests for require_admin dependency."""
    
    @pytest.mark.asyncio
    async def test_require_admin_disabled(self):
        """Test require_admin when admin is disabled."""
        original_value = settings.admin_enabled
        settings.admin_enabled = False
        
        request = Mock()
        request.session = {"is_admin": True}
        
        try:
            with pytest.raises(HTTPException) as exc_info:
                await require_admin(request)
            
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "disabled" in str(exc_info.value.detail).lower()
        finally:
            settings.admin_enabled = original_value
    
    @pytest.mark.asyncio
    async def test_require_admin_not_authenticated(self):
        """Test require_admin when user is not authenticated."""
        original_value = settings.admin_enabled
        settings.admin_enabled = True
        
        request = Mock()
        request.session = {}
        
        try:
            with pytest.raises(HTTPException) as exc_info:
                await require_admin(request)
            
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "login" in str(exc_info.value.detail).lower()
        finally:
            settings.admin_enabled = original_value
    
    @pytest.mark.asyncio
    async def test_require_admin_not_admin(self):
        """Test require_admin when user is authenticated but not admin."""
        original_value = settings.admin_enabled
        settings.admin_enabled = True
        
        request = Mock()
        request.session = {"is_admin": False}
        
        try:
            with pytest.raises(HTTPException) as exc_info:
                await require_admin(request)
            
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        finally:
            settings.admin_enabled = original_value
    
    @pytest.mark.asyncio
    async def test_require_admin_success(self):
        """Test require_admin with valid admin session."""
        original_value = settings.admin_enabled
        settings.admin_enabled = True
        
        request = Mock()
        request.session = {"is_admin": True}
        
        try:
            result = await require_admin(request)
            assert result is True
        finally:
            settings.admin_enabled = original_value


class TestGetOptionalAdmin:
    """Tests for get_optional_admin dependency."""
    
    @pytest.mark.asyncio
    async def test_get_optional_admin_disabled(self):
        """Test get_optional_admin when admin is disabled."""
        original_value = settings.admin_enabled
        settings.admin_enabled = False
        
        request = Mock()
        request.session = {"is_admin": True}
        
        try:
            result = await get_optional_admin(request)
            assert result is False
        finally:
            settings.admin_enabled = original_value
    
    @pytest.mark.asyncio
    async def test_get_optional_admin_not_authenticated(self):
        """Test get_optional_admin when user is not authenticated."""
        original_value = settings.admin_enabled
        settings.admin_enabled = True
        
        request = Mock()
        request.session = {}
        
        try:
            result = await get_optional_admin(request)
            assert result is False
        finally:
            settings.admin_enabled = original_value
    
    @pytest.mark.asyncio
    async def test_get_optional_admin_authenticated(self):
        """Test get_optional_admin when user is authenticated as admin."""
        original_value = settings.admin_enabled
        settings.admin_enabled = True
        
        request = Mock()
        request.session = {"is_admin": True}
        
        try:
            result = await get_optional_admin(request)
            assert result is True
        finally:
            settings.admin_enabled = original_value
    
    @pytest.mark.asyncio
    async def test_get_optional_admin_not_admin(self):
        """Test get_optional_admin when user is not admin."""
        original_value = settings.admin_enabled
        settings.admin_enabled = True
        
        request = Mock()
        request.session = {"is_admin": False}
        
        try:
            result = await get_optional_admin(request)
            assert result is False
        finally:
            settings.admin_enabled = original_value
