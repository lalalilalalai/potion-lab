import json
import logging
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from potion_lab.application import create_app
from potion_lab.settings import Settings
from tests.contract import assert_response_matches_contract

pytestmark = pytest.mark.integration
PATH = "/potions/react"


def potion(effect="healing", power=10, instability=0) -> dict:
    return {
        "name": "PRIVATE_POTION_NAME",
        "effect": effect,
        "power": power,
        "instability": instability,
    }


def test_react_outcomes(caplog: pytest.LogCaptureFixture) -> None:
    cases = (
        (
            [potion(power=18, instability=4), potion(power=12, instability=12)],
            "amplified",
            "healing",
            30,
            16,
        ),
        (
            [potion("speed", 21, 4), potion("strength", 20, 6)],
            "merged",
            "speed",
            20,
            10,
        ),
        ([potion("strength", 10), potion("healing", 10)], "merged", "healing", 10, 0),
        (
            [potion(instability=40), potion(instability=39)],
            "amplified",
            "healing",
            20,
            79,
        ),
        (
            [potion(instability=40), potion(instability=40)],
            "explosion",
            None,
            None,
            None,
        ),
    )
    with caplog.at_level(logging.INFO, logger="potion_lab"):
        with TestClient(create_app(Settings())) as client:
            for pair, outcome, effect, power, instability in cases:
                for ordered in (pair, pair[::-1]):
                    response = client.post(PATH, json={"potions": ordered})
                    assert_response_matches_contract(response, path=PATH, method="post")
                    expected = (
                        None
                        if outcome == "explosion"
                        else {
                            "name": "Лабораторная смесь",
                            "effect": effect,
                            "power": power,
                            "instability": instability,
                        }
                    )
                    assert response.json() == {"outcome": outcome, "potion": expected}
            brewed = client.post(
                "/potions/brew",
                json={
                    "name": "Зелье",
                    "ingredients": [{"ingredient_id": "wind_leaf", "quantity": 1}],
                },
            )
            assert brewed.status_code == 200
            response = client.post(
                PATH, json={"potions": [brewed.json(), brewed.json()]}
            )
            assert_response_matches_contract(response, path=PATH, method="post")
            assert response.json()["potion"]["power"] == 14
    events = [record for record in caplog.records if record.name == "potion_lab"]
    for outcome in ("amplified", "merged", "explosion"):
        expected_level = logging.WARNING if outcome == "explosion" else logging.INFO
        assert any(
            record.levelno == expected_level
            and "status=200 code=ok" in record.getMessage()
            and f"outcome={outcome}" in record.getMessage()
            for record in events
        )
    assert all("PRIVATE_POTION_NAME" not in record.getMessage() for record in events)


def test_react_validation(caplog: pytest.LogCaptureFixture) -> None:
    valid = {"potions": [potion(), potion()]}
    invalid = [None, [], {}, {**valid, "extra": "EXTRA_SECRET"}]
    for potions in ([], [potion()], [potion()] * 3, None, {}, [None, potion()]):
        invalid.append({"potions": potions})
    for field, values in (
        ("name", ("", " \t", "x" * 81, 123, None)),
        ("effect", ("UNKNOWN_SECRET", None, 1)),
        ("power", (0, 101, True, "1", 1.5, None)),
        ("instability", (-1, 101, True, "0", 1.5, None)),
    ):
        for value in values:
            for position in (0, 1):
                payload = deepcopy(valid)
                payload["potions"][position][field] = value
                invalid.append(payload)
    for field in ("name", "effect", "power", "instability"):
        payload = deepcopy(valid)
        del payload["potions"][0][field]
        invalid.append(payload)
    payload = deepcopy(valid)
    payload["potions"][1]["extra"] = "EXTRA_SECRET"
    invalid.append(payload)
    with caplog.at_level(logging.INFO, logger="potion_lab"):
        with TestClient(create_app(Settings())) as client:
            responses = [client.post(PATH), client.post(PATH, content="{invalid")]
            responses.extend(client.post(PATH, json=payload) for payload in invalid)
            for field in ("power", "instability"):
                for value in (float("nan"), float("inf"), float("-inf")):
                    payload = deepcopy(valid)
                    payload["potions"][0][field] = value
                    responses.append(
                        client.post(
                            PATH,
                            content=json.dumps(payload),
                            headers={"Content-Type": "application/json"},
                        )
                    )
            for response in responses:
                assert_response_matches_contract(
                    response, path=PATH, method="post", status=422
                )
                assert all(
                    set(issue) == {"loc", "msg", "type"}
                    for issue in response.json()["detail"]
                )
            for power in (1, 100):
                for instability in (0, 100):
                    response = client.post(
                        PATH,
                        json={
                            "potions": [potion(power=power, instability=instability)]
                            * 2
                        },
                    )
                    assert_response_matches_contract(response, path=PATH, method="post")
    events = "\n".join(
        record.getMessage() for record in caplog.records if record.name == "potion_lab"
    )
    assert "code=validation_error" in events
    assert "PRIVATE_POTION_NAME" not in events
    assert "UNKNOWN_SECRET" not in events
    assert "EXTRA_SECRET" not in events
