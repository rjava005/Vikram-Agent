from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vikram_api.config import Settings
from vikram_api.main import create_app


@pytest.fixture
def api_client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(Settings(data_dir=tmp_path / "data", provider_mode="fake"))
    with TestClient(app) as client:
        yield client
