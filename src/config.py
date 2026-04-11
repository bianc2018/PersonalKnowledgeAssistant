from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


_ENV_CONFIG = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    extra="ignore",
)


class LLMConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="LLM_",
    )
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    enable_search: bool = False


class EmbeddingConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="EMBEDDING_",
    )
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    dimension: int = 768


class SearchConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="SEARCH_",
    )
    provider: str = ""
    api_key: str = ""
    base_url: str = ""


class PrivacySettings(BaseSettings):
    allow_full_content: bool = False
    allow_web_search: bool = True
    allow_log_upload: bool = False


class RetrySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="RETRY_SETTINGS_",
    )
    retry_times: int = 3
    timeout_seconds: int = 30


class StorageSettings(BaseSettings):
    archive_threshold_gb: float = 10.0
    research_concurrency_limit: int = 2
    version_retention_policy: Optional[dict] = None


class LogSettings(BaseSettings):
    level: str = "INFO"
    retention_days: int = 30


class Settings(BaseSettings):
    model_config = _ENV_CONFIG

    database_url: str = Field(default=str(PROJECT_ROOT / "data" / "app.db"))
    secret_key: str = Field(default="change-me-in-production")
    token_expire_hours: int = 24
    remember_me_days: int = 7
    files_dir: Path = Field(default=PROJECT_ROOT / "files")
    log_dir: Path = Field(default=PROJECT_ROOT / "logs")

    llm_config: LLMConfig = Field(default_factory=LLMConfig)
    embedding_config: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    search_config: Optional[SearchConfig] = Field(default=None)
    privacy_settings: PrivacySettings = Field(default_factory=PrivacySettings)
    retry_settings: RetrySettings = Field(default_factory=RetrySettings)
    storage_settings: StorageSettings = Field(default_factory=StorageSettings)
    log_settings: LogSettings = Field(default_factory=LogSettings)


@lru_cache
def get_settings() -> Settings:
    return Settings()
