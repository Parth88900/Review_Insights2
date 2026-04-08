"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI
    openai_api_key: str = "your_openai_api_key_here"
    openai_model: str = "gpt-3.5-turbo"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # CORS
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Rate Limiting
    max_requests_per_minute: int = 30
    scrape_delay_seconds: float = 1.5

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
