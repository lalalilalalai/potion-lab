import logging

import pytest
import yaml
from fastapi.testclient import TestClient

from potion_lab.application import create_app
from potion_lab.settings import Settings
from tests.contract import CONTRACT_PATH, assert_response_matches_contract

pytestmark = pytest.mark.integration


def test_version(caplog: pytest.LogCaptureFixture) -> None:
    contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    with caplog.at_level(logging.INFO, logger="potion_lab"):
        with TestClient(create_app(Settings())) as client:
            response = client.get("/version")
            published = client.get("/openapi.json")
    assert_response_matches_contract(response, path="/version")
    assert published.status_code == 200
    expected = contract["info"]["version"]
    assert response.json() == {"version": expected}
    assert published.json()["info"]["version"] == expected
    assert "method=GET route=/version status=200" in caplog.text
