"""
Application settings and configuration.
"""
import os
from typing import List, Optional
from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    PROJECT_NAME: str = "Telematics UBI POC"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    
    # Database - using SQLite for local development
    DATABASE_URL: str = "sqlite:///./telematics_insurance.db"
    
    # Redis - disabled for local development
    REDIS_URL: Optional[str] = None
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: Optional[int] = None
    
    # JWT Security
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # ML Configuration
    MODEL_RETRAIN_THRESHOLD_DAYS: int = 30
    FEATURE_STORE_PATH: str = "/data/features"
    MODEL_ARTIFACTS_PATH: str = "/models"
    
    # Privacy & Security
    GPS_PRECISION_DECIMALS: int = 5
    DATA_RETENTION_DAYS: int = 365
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Monitoring
    PROMETHEUS_PORT: int = 9090
    GRAFANA_PORT: int = 3000
    GRAFANA_ADMIN_USER: str = "admin"
    GRAFANA_ADMIN_PASSWORD: str = "admin"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    @property
    def database_url(self) -> str:
        """Get database URL."""
        return self.DATABASE_URL
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
