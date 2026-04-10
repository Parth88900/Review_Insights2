"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI
    openai_api_key: str = "your_openai_api_key_here"
    openai_model: str = "gemini-2.5-flash"
    openai_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # CORS
    cors_origins: str = "*"

    max_requests_per_minute: int = 30
    scrape_delay_seconds: float = 0.0

    @property
    def cors_origin_list(self) -> List[str]:
        origins = self.cors_origins.strip()
        if origins == "*":
            return ["*"]
        return [origin.strip() for origin in origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
