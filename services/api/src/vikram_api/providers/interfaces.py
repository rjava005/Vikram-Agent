from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from vikram_api.domain.models import Evidence, ModelAnswer, ParsedEvidence, RetrievedEvidence


class ModelProvider(Protocol):
    provider_id: str
    prompt_version: str

    def answer(
        self, question: str, evidence: Sequence[RetrievedEvidence], timeout_seconds: float
    ) -> ModelAnswer: ...


class EmbeddingProvider(Protocol):
    provider_id: str

    def embed(self, text: str, timeout_seconds: float) -> tuple[float, ...]: ...


class RetrievalProvider(Protocol):
    provider_id: str

    def search(
        self,
        question: str,
        evidence: Sequence[Evidence],
        embedding_provider: EmbeddingProvider,
        timeout_seconds: float,
        limit: int = 4,
    ) -> list[RetrievedEvidence]: ...


class SpeechToTextProvider(Protocol):
    provider_id: str

    def transcribe(self, audio: bytes, timeout_seconds: float) -> str: ...


class TextToSpeechProvider(Protocol):
    provider_id: str

    def synthesize(self, text: str, timeout_seconds: float) -> bytes: ...


class BlobStorageProvider(Protocol):
    provider_id: str

    def put(self, content: bytes, timeout_seconds: float) -> str: ...

    def read(self, key: str, timeout_seconds: float) -> bytes: ...


class DocumentParser(Protocol):
    parser_id: str

    def parse(self, content: bytes) -> list[ParsedEvidence]: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class LocalBlobStorage:
    provider_id = "local-content-addressed-v1"

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, content: bytes, timeout_seconds: float) -> str:
        del timeout_seconds
        import hashlib

        digest = hashlib.sha256(content).hexdigest()
        key = f"sha256/{digest}"
        target = self.root / "sha256" / digest
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            temporary = target.with_name(f".{digest}.{uuid4().hex}.tmp")
            try:
                temporary.write_bytes(content)
                try:
                    temporary.replace(target)
                except PermissionError:
                    if not target.exists():
                        raise
            finally:
                temporary.unlink(missing_ok=True)
        return key

    def read(self, key: str, timeout_seconds: float) -> bytes:
        del timeout_seconds
        prefix, separator, digest = key.partition("/")
        if prefix != "sha256" or not separator or len(digest) != 64:
            raise ValueError("Invalid blob key")
        return (self.root / prefix / digest).read_bytes()


class SystemClock:
    def now(self) -> datetime:
        from vikram_api.domain.models import utc_now

        return utc_now()
