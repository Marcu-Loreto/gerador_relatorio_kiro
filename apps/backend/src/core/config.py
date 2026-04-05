"""Application configuration."""
import os
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> Optional[str]:
    """Find .env file searching up from cwd."""
    candidates = [
        ".env",
        "../../.env",
        os.path.join(os.path.dirname(__file__), "../../../../.env"),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return ".env"


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "gerador_relatorio_kiro"
    app_version: str = "1.0.0"
    environment: str = "development"

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_reload: bool = True
    backend_workers: int = 4

    # Database
    database_url: str = "sqlite:///./app.db"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 3600

    # Storage
    storage_type: str = "local"
    storage_local_path: str = "./uploads"
    s3_bucket: str = ""
    s3_region: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""

    # Security — use plain strings to avoid pydantic-settings JSON parsing issues
    secret_key: str = "dev-secret-key-change-in-production-min32chars"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440
    allowed_origins_str: str = "http://localhost:5173,http://localhost:3000,http://localhost:8000"

    @property
    def allowed_origins(self) -> List[str]:
        return [s.strip() for s in self.allowed_origins_str.split(",") if s.strip()]

    # LLM Configuration
    openai_api_key: str = ""
    minimax_api_key: str = ""

    # Model Selection Strategy
    model_selection_strategy: str = "auto"
    simple_model: str = "minimax-m2.5"
    complex_model: str = "gpt-4o"

    # Model Parameters
    default_temperature: float = 0.3
    default_max_tokens: int = 4096
    simple_task_max_tokens: int = 2048
    complex_task_max_tokens: int = 8192

    # File Upload
    max_upload_size_mb: int = 50
    allowed_extensions_str: str = ".pdf,.docx,.xlsx,.csv,.txt,.pptx,.md"

    @property
    def allowed_extensions(self) -> List[str]:
        return [s.strip() for s in self.allowed_extensions_str.split(",") if s.strip()]

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # Observability
    otel_enabled: bool = False
    otel_endpoint: str = "http://localhost:4318"
    log_level: str = "INFO"
    log_format: str = "json"

    # Security Features
    enable_security_guard: bool = True
    enable_prompt_injection_detection: bool = True
    max_revision_attempts: int = 3

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
