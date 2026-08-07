from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VIKRAM_", extra="ignore")

    data_dir: Path = Field(default=Path(".vikram"))
    host: str = "127.0.0.1"
    port: int = Field(default=8742, ge=1024, le=65535)
    provider_mode: str = "fake"
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173,null"
    max_source_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)
    provider_timeout_seconds: float = Field(default=8.0, gt=0, le=60)

    @property
    def database_path(self) -> Path:
        return self.data_dir / "vikram.sqlite3"

    @property
    def blob_dir(self) -> Path:
        return self.data_dir / "blobs"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
