"""
Configuration settings
"""

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Vision Attendance System"
    version: str = "2.0.0"
    debug: bool = True
    secret_key: str = "your-secret-key-change-this"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    class Config:
        env_file = ".env"

settings = Settings()