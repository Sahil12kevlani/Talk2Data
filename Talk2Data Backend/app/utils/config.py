from pydantic_settings import BaseSettings
from typing import Dict, Optional
import json
import os

class Settings(BaseSettings):
    # Backwards compatible single DB envs
    database_url: Optional[str] = None
    food_db_url: Optional[str] = None

    # Preferred: JSON mapping for multiple DBs
    database_urls: Dict[str, str] = {}  # pydantic will parse JSON string automatically if env var is JSON

    groq_api_key: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    # helper to unify sources
    def all_databases(self) -> Dict[str, str]:
        # priority: explicit database_urls if provided, else fallback to explicit urls
        urls = dict(self.database_urls or {})
        if not urls:
            if self.database_url:
                urls["talk2data"] = self.database_url
            if self.food_db_url:
                urls["fooddb"] = self.food_db_url
        return urls

settings = Settings()
