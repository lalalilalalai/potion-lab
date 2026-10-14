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
            docs = client.get("/docs?token=QUERY_SECRET")
            unknown = client.get("/PRIVATE_PATH_SECRET")
    assert_response_matches_contract(response, path="/version")
    assert published.status_code == 200
    assert docs.status_code == 200
    assert unknown.status_code == 404
    expected = contract["info"]["version"]
    assert response.json() == {"version": expected}
    assert published.json()["info"]["version"] == expected
    assert "method=GET route=/version status=200" in caplog.text
    assert "method=GET route=/openapi.json status=200" in caplog.text
    assert "method=GET route=/docs status=200" in caplog.text
    events = "\n".join(
        record.getMessage() for record in caplog.records if record.name == "potion_lab"
    )
    assert "route=<неизвестный> status=404" in events
    assert "QUERY_SECRET" not in events
    assert "PRIVATE_PATH_SECRET" not in events
