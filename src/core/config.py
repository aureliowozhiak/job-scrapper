"""Configuration management for the job scrapper application."""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Authentication settings
    admin_enabled: bool = True
    admin_username: str = "admin"
    admin_password_hash: str = ""
    session_secret_key: str = ""
    
    # Database settings
    database_url: str = "sqlite:///./jobs.db"
    
    # Application settings
    app_name: str = "Job Scrapper"
    debug: bool = False
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = False
    
    def validate_production_settings(self) -> None:
        """Validate that required settings are configured for production."""
        if not self.debug:
            if not self.admin_password_hash:
                raise ValueError(
                    "ADMIN_PASSWORD_HASH must be set in production. "
                    "Generate one using: python -c \"from passlib.hash import bcrypt; print(bcrypt.hash('your_password'))\""
                )
            if not self.session_secret_key:
                raise ValueError(
                    "SESSION_SECRET_KEY must be set in production. "
                    "Generate one using: python -c \"import secrets; print(secrets.token_hex(32))\""
                )


# Global settings instance
settings = Settings()
