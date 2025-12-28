"""
Configuration module for Quantum Circuit API Server.

Loads configuration from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server configuration
    port: int = 8000
    log_level: str = "INFO"
    environment: str = "development"

    # CORS configuration
    cors_origins: str = "*"

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
