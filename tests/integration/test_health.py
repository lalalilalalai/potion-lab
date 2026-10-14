import logging

import pytest
from fastapi.testclient import TestClient

from potion_lab.application import create_app
from potion_lab.settings import Settings
from tests.contract import assert_response_matches_contract

pytestmark = pytest.mark.integration


def test_health(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="potion_lab"):
        with TestClient(create_app(Settings())) as client:
            response = client.get(
                "/health?token=QUERY_SECRET",
                headers={"Authorization": "Bearer HEADER_SECRET"},
            )
    assert_response_matches_contract(response, path="/health")
    assert response.json() == {"status": "ok"}
    assert "APP_NAME='potion-lab'" in caplog.text
    assert "APP_VERSION=1.0.0" in caplog.text
    assert "method=GET route=/health status=200" in caplog.text
    assert "Приложение остановлено" in caplog.text
    events = "\n".join(
        record.getMessage() for record in caplog.records if record.name == "potion_lab"
    )
    assert "QUERY_SECRET" not in events
    assert "HEADER_SECRET" not in events
