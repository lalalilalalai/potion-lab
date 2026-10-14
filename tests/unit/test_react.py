from itertools import combinations

import pytest

from generated.dto import Effect, Potion, ReactRequest
from potion_lab.domain import react_potions

pytestmark = pytest.mark.unit


def potion(effect=Effect.healing, power=10, instability=0) -> Potion:
    return Potion(
        name="Исходное зелье", effect=effect, power=power, instability=instability
    )


def test_react_amplifies_same_effect_and_caps_power() -> None:
    for effect in Effect:
        result = react_potions(
            ReactRequest(potions=[potion(effect, 80, 30), potion(effect, 90, 49)])
        ).model_dump(mode="json")
        assert result == {
            "outcome": "amplified",
            "potion": {
                "name": "Лабораторная смесь",
                "effect": effect.value,
                "power": 100,
                "instability": 79,
            },
        }


def test_react_merges_by_power_then_contract_priority_and_rounds_down() -> None:
    result = react_potions(
        ReactRequest(potions=[potion(Effect.strength, 21), potion(Effect.healing, 20)])
    ).model_dump(mode="json")
    assert result["outcome"] == "merged"
    assert result["potion"]["effect"] == "strength"
    assert result["potion"]["power"] == 20
    priority = (Effect.healing, Effect.invisibility, Effect.speed, Effect.strength)
    for winner, loser in combinations(priority, 2):
        result = react_potions(
            ReactRequest(potions=[potion(loser), potion(winner)])
        ).model_dump(mode="json")
        assert result["potion"]["effect"] == winner.value
        assert result["potion"]["power"] == 10


def test_react_explosion_threshold_precedes_other_rules() -> None:
    for effect in (Effect.healing, Effect.strength):
        for first, second in ((40, 40), (79, 1), (100, 100)):
            result = react_potions(
                ReactRequest(
                    potions=[
                        potion(instability=first),
                        potion(effect, instability=second),
                    ]
                )
            ).model_dump(mode="json")
            assert result == {"outcome": "explosion", "potion": None}
        result = react_potions(
            ReactRequest(
                potions=[potion(instability=40), potion(effect, instability=39)]
            )
        ).model_dump(mode="json")
        assert result["potion"]["instability"] == 79


def test_react_is_symmetric_and_does_not_change_inputs() -> None:
    pairs = (
        [potion(power=1), potion(power=2)],
        [potion(Effect.speed, 21), potion(Effect.strength, 20)],
        [potion(instability=80), potion()],
    )
    for pair in pairs:
        before = [item.model_dump(mode="json") for item in pair]
        forward = react_potions(ReactRequest(potions=pair))
        backward = react_potions(ReactRequest(potions=pair[::-1]))
        assert forward == backward
        assert [item.model_dump(mode="json") for item in pair] == before
