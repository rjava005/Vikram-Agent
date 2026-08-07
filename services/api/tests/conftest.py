from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vikram_api.app_factory import API_TOKEN_HEADER, create_app
from vikram_api.config import Settings

TEST_API_TOKEN = "test-local-capability-token-000000000000000000"


@pytest.fixture
def api_client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(
        Settings(data_dir=tmp_path / "data", provider_mode="fake", api_token=TEST_API_TOKEN)
    )
    with TestClient(app) as client:
        client.headers[API_TOKEN_HEADER] = TEST_API_TOKEN
        yield client
