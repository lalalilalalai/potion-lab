import logging

import pytest
import yaml
from fastapi.testclient import TestClient

from potion_lab.application import create_app
from potion_lab.settings import Settings
from tests.contract import CONTRACT_PATH, assert_response_matches_contract

pytestmark = pytest.mark.integration


def test_ingredients(caplog: pytest.LogCaptureFixture) -> None:
    contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    expected = contract["paths"]["/ingredients"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["example"]
    with caplog.at_level(logging.INFO, logger="potion_lab"):
        with TestClient(create_app(Settings())) as client:
            response = client.get("/ingredients")
    assert_response_matches_contract(response, path="/ingredients")
    assert len(response.json()) == 5
    assert response.json() == expected
    assert "method=GET route=/ingredients status=200" in caplog.text
