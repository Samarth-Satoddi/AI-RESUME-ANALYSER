import os
from typing import List, Union
from pydantic import Field, field_validator
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "AI Resume Analyzer & Job Opportunity Matcher"
    API_V1_STR: str = "/api/v1"

    # Security & Auth
    SECRET_KEY: str = "temporary-secret-key-change-in-production-min-32-chars-long"
    JWT_SECRET_KEY: str = "temporary-jwt-secret-key-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_MIN_LENGTH: int = 8

    # Database
    # Default to sqlite locally if PostgreSQL is not active; will use DATABASE_URL from .env
    DATABASE_URL: str = "sqlite:///./resume_analyzer.db"

    # Redis & Background Tasks
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: List[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    ]

    # AI & Embeddings
    AI_PROVIDER: str = "heuristic"  # 'heuristic', 'openai', 'anthropic'
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: str = ""
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Scoring Weights (Configurable)
    WEIGHT_SKILL: float = 0.35
    WEIGHT_SEMANTIC: float = 0.25
    WEIGHT_EXPERIENCE: float = 0.20
    WEIGHT_KEYWORD: float = 0.10
    WEIGHT_EDUCATION: float = 0.10

    # Job Search Agent Configuration
    JOB_SEARCH_ENABLED: bool = True
    JOB_SEARCH_PROVIDER: str = "mock"  # 'mock', 'remotive', 'arbeitnow', 'adzuna', 'custom'
    JOB_SEARCH_API_KEY: str = ""
    JOB_SEARCH_API_URL: str = ""
    JOB_SEARCH_MAX_SOURCES: int = 5
    JOB_SEARCH_MAX_RESULTS_PER_SOURCE: int = 50
    JOB_SEARCH_MAX_TOTAL_RESULTS: int = 100
    JOB_SEARCH_TIMEOUT_SECONDS: int = 30
    JOB_SEARCH_CACHE_TTL: int = 900
    JOB_SEARCH_RANK_WEIGHT_MATCH: float = 0.60
    JOB_SEARCH_RANK_WEIGHT_SKILL: float = 0.20
    JOB_SEARCH_RANK_WEIGHT_LOCATION: float = 0.10
    JOB_SEARCH_RANK_WEIGHT_FRESHNESS: float = 0.10

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]


settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
