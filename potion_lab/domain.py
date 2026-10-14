"""Справочник и вычисления лаборатории без зависимости от HTTP-фреймворка."""

from generated.dto import BrewRequest, Effect, Ingredient, IngredientId, Potion

EFFECT_PRIORITY = (Effect.healing, Effect.invisibility, Effect.speed, Effect.strength)


class DuplicateIngredientError(ValueError):
    """В рецепте повторяется один ингредиент."""


_INGREDIENTS = (
    Ingredient(
        id=IngredientId.moon_dust,
        name="Лунная пыль",
        effect=Effect.invisibility,
        potency=8,
        instability=3,
    ),
    Ingredient(
        id=IngredientId.dragon_scale,
        name="Чешуя дракона",
        effect=Effect.strength,
        potency=10,
        instability=5,
    ),
    Ingredient(
        id=IngredientId.phoenix_feather,
        name="Перо феникса",
        effect=Effect.healing,
        potency=9,
        instability=2,
    ),
    Ingredient(
        id=IngredientId.wind_leaf,
        name="Лист ветра",
        effect=Effect.speed,
        potency=7,
        instability=1,
    ),
    Ingredient(
        id=IngredientId.troll_moss,
        name="Мох тролля",
        effect=Effect.healing,
        potency=4,
        instability=4,
    ),
)


def list_ingredients() -> list[Ingredient]:
    """Вернуть копии, чтобы вызывающий код не изменил нормативный справочник."""
    return [ingredient.model_copy(deep=True) for ingredient in _INGREDIENTS]


def brew_potion(recipe: BrewRequest) -> Potion:
    ids = [portion.ingredient_id for portion in recipe.ingredients]
    if len(set(ids)) != len(ids):
        raise DuplicateIngredientError
    catalog = {ingredient.id: ingredient for ingredient in _INGREDIENTS}
    scores = dict.fromkeys(EFFECT_PRIORITY, 0)
    instability = 0
    for portion in recipe.ingredients:
        ingredient = catalog[portion.ingredient_id]
        scores[ingredient.effect] += ingredient.potency * portion.quantity
        instability += ingredient.instability * portion.quantity
    effect = max(EFFECT_PRIORITY, key=scores.__getitem__)
    return Potion(
        name=recipe.name,
        effect=effect,
        power=min(scores[effect], 100),
        instability=min(instability, 100),
    )
