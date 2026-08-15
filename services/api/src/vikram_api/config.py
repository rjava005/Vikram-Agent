from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VIKRAM_", extra="ignore", populate_by_name=True)

    data_dir: Path = Field(default=Path(".vikram"))
    host: str = "127.0.0.1"
    port: int = Field(default=8742, ge=1024, le=65535)
    provider_mode: Literal["fake", "nebius"] = "fake"
    api_token: str = Field(default="", max_length=256)
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173,null"
    max_source_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)
    provider_timeout_seconds: float = Field(default=8.0, gt=0, le=60)
    nebius_api_key: str = Field(default="", validation_alias="NEBIUS_API_KEY", repr=False)
    nebius_generation_model: str = "Qwen/Qwen3-30B-A3B-Instruct-2507"
    nebius_embedding_model: str = "Qwen/Qwen3-Embedding-8B"
    nebius_timeout_seconds: float = Field(default=45.0, gt=0, le=60)
    nebius_embedding_dimensions: int = Field(default=4096, ge=32, le=4096)
    nebius_embedding_batch_size: int = Field(default=16, ge=1, le=64)
    nebius_max_evidence_units: int = Field(default=256, ge=1, le=2048)
    nebius_max_evidence_characters: int = Field(default=12_000, ge=1_000, le=24_000)
    nebius_retrieval_limit: int = Field(default=4, ge=1, le=4)

    @property
    def remote_ai_configured(self) -> bool:
        return self.provider_mode == "nebius" and bool(self.nebius_api_key)

    @property
    def database_path(self) -> Path:
        return self.data_dir / "vikram.sqlite3"

    @property
    def blob_dir(self) -> Path:
        return self.data_dir / "blobs"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
