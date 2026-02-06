from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # App
    app_name: str = "Job Scrapper Pro"
    app_version: str = "3.0.0"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    
    # Database
    database_url: str = "sqlite:///./data/db/jobs.db"
    database_echo: bool = False
    
    # Paths
    data_lake_path: Path = Path("data/lake")
    output_path: Path = Path("data/output")
    logs_path: Path = Path("data/logs")
    
    # API
    api_prefix: str = "/api"
    docs_url: str = "/api/docs"
    redoc_url: str = "/api/redoc"
    
    # Background Jobs
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_url: Optional[str] = None
    
    @model_validator(mode='after')
    def assemble_redis_url(self) -> 'Settings':
        """Construct redis URL from components if not provided."""
        if not self.redis_url:
            auth = f":{self.redis_password}@" if self.redis_password else ""
            self.redis_url = f"redis://{auth}{self.redis_host}:{self.redis_port}/0"
        return self

    enable_background_jobs: bool = True
    job_timeout: int = 3600  # 1 hour
    job_result_ttl: int = 3600  # 1 hour
    
    # Scraper
    max_retries: int = 3
    retry_delay: int = 2
    request_timeout: int = 30
    
    # Validation
    enable_pre_validation: bool = True
    pre_validation_sample_size: int = 100
    validation_batch_size: int = 50
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()
