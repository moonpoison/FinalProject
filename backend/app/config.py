from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
from typing import List
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AutoFlow API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./autoflow.db"

    # JWT
    SECRET_KEY: str = "autoflow-secret-key-change-in-production-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Claude API
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

    # OpenAI API (for Whisper)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # PortOne (결제)
    PORTONE_API_SECRET: str = os.getenv("PORTONE_API_SECRET", "")

    # CORS - 문자열로 받고 파싱
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001"

    @property
    def cors_origins_list(self) -> List[str]:
        """CORS_ORIGINS를 리스트로 반환"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
