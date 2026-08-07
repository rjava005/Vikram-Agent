from __future__ import annotations

from vikram_api.app_factory import create_app
from vikram_api.config import Settings

app = create_app()


def run() -> None:
    import uvicorn

    settings = Settings()
    uvicorn.run("vikram_api.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    run()
