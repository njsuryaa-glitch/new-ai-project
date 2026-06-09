from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    PROJECT_NAME: str = "AI Knowledge Assistant API"
    API_KEY: str = "default-secret-key"
    
    # Database Settings
    # default local fallback if not defined
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/rag_db"
    
    # Redis Cache/Queue Settings
    REDIS_URL: str = "redis://localhost:6379/0"
    ENABLE_REDIS: bool = False
    
    # Gemini Settings
    GEMINI_API_KEY: str = ""
    
    # Document Settings
    MAX_FILE_SIZE_MB: int = 10
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


settings = Settings()
