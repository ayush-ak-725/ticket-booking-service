import os
from typing import Optional
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Application configuration"""
    
    # Application settings
    app_name: str = "Ayush_Kumar_Agrawal's Box Office"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8080
    
    # Redis settings
    redis_url: str = "redis://localhost:6379"
    
    # Celery settings
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # Hold settings
    hold_ttl_minutes: int = 2
    hold_ttl_min_seconds: int = 10      # sensible lower cap
    hold_ttl_max_seconds: int = 900     # 15 minutes upper cap
    max_hold_quantity: int = 100
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Metrics
    enable_metrics: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global config instance
config = Config()
