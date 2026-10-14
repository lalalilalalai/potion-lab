"""Справочник и вычисления лаборатории без зависимости от HTTP-фреймворка."""

from generated.dto import Effect, Ingredient, IngredientId

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
