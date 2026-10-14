from itertools import combinations
from math import lcm

import pytest

from generated.dto import BrewRequest, Effect
from potion_lab.domain import DuplicateIngredientError, brew_potion, list_ingredients

pytestmark = pytest.mark.unit


def test_brew_adds_points_of_same_effect_and_preserves_name() -> None:
    recipe = BrewRequest.model_validate(
        {
            "name": "  Бальзам  ",
            "ingredients": [
                {"ingredient_id": "phoenix_feather", "quantity": 2},
                {"ingredient_id": "troll_moss", "quantity": 3},
                {"ingredient_id": "dragon_scale", "quantity": 2},
            ],
        }
    )
    result = brew_potion(recipe)
    assert result.model_dump(mode="json") == {
        "name": "  Бальзам  ",
        "effect": "healing",
        "power": 30,
        "instability": 26,
    }


def test_brew_breaks_all_effect_ties_by_contract_priority() -> None:
    priority = (Effect.healing, Effect.invisibility, Effect.speed, Effect.strength)
    catalog = list_ingredients()
    for winner, loser in combinations(priority, 2):
        first = next(item for item in catalog if item.effect == winner)
        second = next(item for item in catalog if item.effect == loser)
        score = lcm(first.potency, second.potency)
        portions = [
            {"ingredient_id": first.id, "quantity": score // first.potency},
            {"ingredient_id": second.id, "quantity": score // second.potency},
        ]
        for ordered in (portions, portions[::-1]):
            recipe = BrewRequest.model_validate(
                {"name": "Равенство", "ingredients": ordered}
            )
            result = brew_potion(recipe)
            assert result.effect == winner
            assert result.power == min(score, 100)


def test_brew_caps_power_and_total_instability() -> None:
    recipe = BrewRequest.model_validate(
        {
            "name": "Максимум",
            "ingredients": [
                {"ingredient_id": item.id, "quantity": 10}
                for item in list_ingredients()
            ],
        }
    )
    result = brew_potion(recipe)
    assert result.effect == Effect.healing
    assert result.power == 100
    assert result.instability == 100


def test_brew_rejects_duplicate_ingredient() -> None:
    recipe = BrewRequest.model_validate(
        {
            "name": "Дубликат",
            "ingredients": [
                {"ingredient_id": "moon_dust", "quantity": 1},
                {"ingredient_id": "moon_dust", "quantity": 2},
            ],
        }
    )
    with pytest.raises(DuplicateIngredientError):
        brew_potion(recipe)
