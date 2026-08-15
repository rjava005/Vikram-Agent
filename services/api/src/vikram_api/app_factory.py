from __future__ import annotations

import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from vikram_api.config import Settings
from vikram_api.contracts import AiRuntimeResponse, HealthResponse, ProblemResponse
from vikram_api.domain.models import DomainError
from vikram_api.providers.fake import (
    DeterministicEmbeddingProvider,
    DeterministicModelProvider,
    DeterministicRetrievalProvider,
    DeterministicSpeechToTextProvider,
    DeterministicTextToSpeechProvider,
)
from vikram_api.providers.interfaces import LocalBlobStorage, SystemClock
from vikram_api.providers.nebius import (
    NebiusEmbeddingProvider,
    NebiusGroundedModelProvider,
    NebiusHttpClient,
)
from vikram_api.repositories.sqlite import SqliteRepository
from vikram_api.routes.v1 import router as v1_router
from vikram_api.services.grounded import RemoteGroundedPipeline
from vikram_api.services.workspace import VikramService

API_TOKEN_HEADER = "X-Vikram-Token"


def create_app(
    settings: Settings | None = None,
    *,
    remote_grounding: RemoteGroundedPipeline | None = None,
    remote_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    runtime = settings or Settings()
    if len(runtime.api_token) < 43:
        raise RuntimeError("VIKRAM_API_TOKEN must be a high-entropy per-launch local capability.")
    repository = SqliteRepository(runtime.database_path)
    owned_remote_client: NebiusHttpClient | None = None
    if runtime.provider_mode == "nebius":
        if not runtime.nebius_api_key:
            raise RuntimeError("NEBIUS_API_KEY is required when VIKRAM_PROVIDER_MODE=nebius.")
        if remote_grounding is None:
            owned_remote_client = NebiusHttpClient(
                api_key=runtime.nebius_api_key,
                timeout_seconds=runtime.nebius_timeout_seconds,
                transport=remote_transport,
            )
            remote_embeddings = NebiusEmbeddingProvider(
                owned_remote_client,
                model_id=runtime.nebius_embedding_model,
                dimensions=runtime.nebius_embedding_dimensions,
                max_batch_size=runtime.nebius_embedding_batch_size,
                max_input_characters=runtime.nebius_max_evidence_characters,
            )
            remote_model = NebiusGroundedModelProvider(
                owned_remote_client,
                generation_model_id=runtime.nebius_generation_model,
                max_evidence_items=runtime.nebius_retrieval_limit,
                max_evidence_characters=runtime.nebius_max_evidence_characters,
            )
            remote_grounding = RemoteGroundedPipeline(
                settings=runtime,
                repository=repository,
                embeddings=remote_embeddings,
                model=remote_model,
            )
    service = VikramService(
        settings=runtime,
        repository=repository,
        storage=LocalBlobStorage(runtime.blob_dir),
        model=DeterministicModelProvider(),
        embeddings=DeterministicEmbeddingProvider(),
        retrieval=DeterministicRetrievalProvider(),
        speech_to_text=DeterministicSpeechToTextProvider(),
        text_to_speech=DeterministicTextToSpeechProvider(),
        clock=SystemClock(),
        remote_grounding=remote_grounding,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        if owned_remote_client is not None:
            await owned_remote_client.aclose()

    app = FastAPI(
        title="Vikram API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.vikram_service = service
    app.state.settings = runtime
    app.add_middleware(
        CORSMiddleware,
        allow_origins=runtime.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["Content-Type", API_TOKEN_HEADER],
    )

    @app.middleware("http")
    async def require_local_capability(request: Request, call_next: object) -> object:
        if request.method != "OPTIONS" and request.url.path.startswith("/api/v1"):
            supplied = request.headers.get(API_TOKEN_HEADER, "")
            if not secrets.compare_digest(supplied, runtime.api_token):
                problem = ProblemResponse(
                    type="https://vikram.local/problems/unauthorized",
                    title="Unauthorized",
                    status=401,
                    detail="A valid local desktop capability is required.",
                    code="unauthorized",
                )
                return JSONResponse(
                    status_code=401,
                    content=problem.model_dump(mode="json"),
                    media_type="application/problem+json",
                )
        return await call_next(request)  # type: ignore[operator]

    app.include_router(v1_router)

    @app.exception_handler(DomainError)
    async def handle_domain_error(_request: Request, error: DomainError) -> JSONResponse:
        problem = ProblemResponse(
            type=error.problem_type,
            title=error.title,
            status=error.status_code,
            detail=str(error),
            code=error.code,
            retryable=error.retryable,
        )
        return JSONResponse(
            status_code=error.status_code,
            content=problem.model_dump(mode="json"),
            media_type="application/problem+json",
        )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        if runtime.provider_mode == "nebius":
            generation_model = runtime.nebius_generation_model
            embedding_model = runtime.nebius_embedding_model
        else:
            generation_model = "fake-extractive-model-v1"
            embedding_model = "fake-hash-embedding-v1"
        return HealthResponse(
            provider_mode=runtime.provider_mode,
            ai_runtime=AiRuntimeResponse(
                provider_mode=runtime.provider_mode,
                remote_configured=runtime.remote_ai_configured,
                generation_model=generation_model,
                embedding_model=embedding_model,
            ),
        )

    return app
