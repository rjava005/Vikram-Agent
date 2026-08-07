from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from vikram_api.config import Settings
from vikram_api.contracts import HealthResponse, ProblemResponse
from vikram_api.domain.models import DomainError
from vikram_api.providers.fake import (
    DeterministicEmbeddingProvider,
    DeterministicModelProvider,
    DeterministicRetrievalProvider,
    DeterministicSpeechToTextProvider,
    DeterministicTextToSpeechProvider,
)
from vikram_api.providers.interfaces import LocalBlobStorage, SystemClock
from vikram_api.repositories.sqlite import SqliteRepository
from vikram_api.routes.v1 import router as v1_router
from vikram_api.services.workspace import VikramService


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime = settings or Settings()
    if runtime.provider_mode != "fake":
        raise RuntimeError(
            "Only VIKRAM_PROVIDER_MODE=fake is available in this milestone; real providers require explicit configuration and evaluation."
        )
    repository = SqliteRepository(runtime.database_path)
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
    )
    app = FastAPI(title="Vikram API", version="1.0.0", docs_url="/docs", redoc_url=None)
    app.state.vikram_service = service
    app.state.settings = runtime
    app.add_middleware(
        CORSMiddleware,
        allow_origins=runtime.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    app.include_router(v1_router)

    @app.exception_handler(DomainError)
    async def handle_domain_error(_request: Request, error: DomainError) -> JSONResponse:
        problem = ProblemResponse(
            type=error.problem_type,
            title=error.title,
            status=error.status_code,
            detail=str(error),
        )
        return JSONResponse(
            status_code=error.status_code,
            content=problem.model_dump(mode="json"),
            media_type="application/problem+json",
        )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(provider_mode=runtime.provider_mode)

    return app


app = create_app()


def run() -> None:
    import uvicorn

    settings = Settings()
    uvicorn.run("vikram_api.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    run()
