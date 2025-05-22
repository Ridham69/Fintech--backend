from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from typing import Optional
import os

# Load environment variables from .env file if present
load_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: Optional[str] = None
    SECRET_KEY: str
    ENV: str = "development"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
