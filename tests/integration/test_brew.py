import logging
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from potion_lab.application import create_app
from potion_lab.settings import Settings
from tests.contract import assert_response_matches_contract

pytestmark = pytest.mark.integration
PATH = "/potions/brew"


def test_brew_success(caplog: pytest.LogCaptureFixture) -> None:
    payload = {
        "name": "Эликсир тихого шага",
        "ingredients": [
            {"ingredient_id": "moon_dust", "quantity": 2},
            {"ingredient_id": "wind_leaf", "quantity": 1},
        ],
    }
    with caplog.at_level(logging.INFO, logger="potion_lab"):
        with TestClient(create_app(Settings())) as client:
            response = client.post(PATH, json=payload)
            again = client.post(PATH, json=payload)
    assert_response_matches_contract(response, path=PATH, method="post")
    assert_response_matches_contract(again, path=PATH, method="post")
    assert response.json() == {
        "name": payload["name"],
        "effect": "invisibility",
        "power": 16,
        "instability": 7,
    }
    assert again.json() == response.json()
    assert "method=POST route=/potions/brew status=200 code=ok" in caplog.text
    assert payload["name"] not in caplog.text


def test_brew_duplicate(caplog: pytest.LogCaptureFixture) -> None:
    payload = {
        "name": "PRIVATE_POTION_NAME",
        "ingredients": [
            {"ingredient_id": "moon_dust", "quantity": 1},
            {"ingredient_id": "moon_dust", "quantity": 2},
        ],
    }
    with caplog.at_level(logging.INFO, logger="potion_lab"):
        with TestClient(create_app(Settings())) as client:
            response = client.post(PATH, json=payload)
    assert_response_matches_contract(response, path=PATH, method="post", status=400)
    assert response.json() == {
        "detail": {
            "code": "duplicate_ingredient",
            "message": "Каждый ингредиент можно указать только один раз.",
        }
    }
    events = [record for record in caplog.records if record.name == "potion_lab"]
    assert any(
        record.levelno == logging.WARNING
        and "code=duplicate_ingredient" in record.getMessage()
        for record in events
    )
    assert "PRIVATE_POTION_NAME" not in caplog.text


def test_brew_validation(caplog: pytest.LogCaptureFixture) -> None:
    valid = {
        "name": "Зелье",
        "ingredients": [{"ingredient_id": "moon_dust", "quantity": 1}],
    }
    invalid = [None, [], {}, {"name": "Зелье"}, {"ingredients": valid["ingredients"]}]
    for name in ("", " \t\n", "x" * 81, 123, None):
        invalid.append({**valid, "name": name})
    for ingredients in ([], valid["ingredients"] * 6, None, {}, [None]):
        invalid.append({**valid, "ingredients": ingredients})
    for quantity in (0, 11, -1, True, "2", 1.5, None):
        payload = deepcopy(valid)
        payload["ingredients"][0]["quantity"] = quantity
        invalid.append(payload)
    invalid.extend(
        [
            {**valid, "extra": "PRIVATE_EXTRA"},
            {
                **valid,
                "ingredients": [{"ingredient_id": "UNKNOWN_SECRET", "quantity": 1}],
            },
            {**valid, "ingredients": [{"ingredient_id": "moon_dust"}]},
            {**valid, "ingredients": [{"quantity": 1}]},
            {
                **valid,
                "ingredients": [
                    {"ingredient_id": "moon_dust", "quantity": 1, "extra": True}
                ],
            },
        ]
    )
    with caplog.at_level(logging.INFO, logger="potion_lab"):
        with TestClient(create_app(Settings())) as client:
            responses = [client.post(PATH), client.post(PATH, content="{invalid")]
            responses.extend(client.post(PATH, json=payload) for payload in invalid)
            for value in ("NaN", "Infinity", "-Infinity"):
                responses.append(
                    client.post(
                        PATH,
                        content='{"name":"Зелье","ingredients":[{"ingredient_id":'
                        '"moon_dust","quantity":' + value + "}]}",
                        headers={"Content-Type": "application/json"},
                    )
                )
            for response in responses:
                assert_response_matches_contract(
                    response, path=PATH, method="post", status=422
                )
                assert response.json()["detail"]
                assert all(
                    set(issue) == {"loc", "msg", "type"}
                    for issue in response.json()["detail"]
                )
            for name in ("x", "x" * 80):
                for quantity in (1, 10):
                    response = client.post(
                        PATH,
                        json={
                            "name": name,
                            "ingredients": [
                                {"ingredient_id": "moon_dust", "quantity": quantity}
                            ],
                        },
                    )
                    assert_response_matches_contract(response, path=PATH, method="post")
    events = "\n".join(
        record.getMessage() for record in caplog.records if record.name == "potion_lab"
    )
    assert "code=validation_error" in events
    assert "UNKNOWN_SECRET" not in events
    assert "PRIVATE_EXTRA" not in events
