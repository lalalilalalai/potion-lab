from copy import deepcopy

import pytest
import yaml

from tests.contract import CONTRACT_PATH, canonical_schema

pytestmark = pytest.mark.unit


def test_schema_comparison_preserves_contract_constraints() -> None:
    source = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    schema = {"$ref": "#/components/schemas/BrewRequest"}
    original = canonical_schema(schema, source)
    mutations = (
        ("IngredientPortion", "quantity", "maximum", 11),
        ("IngredientPortion", "quantity", "minimum", 0),
        ("BrewRequest", "name", "maxLength", 81),
        ("BrewRequest", "name", "pattern", ".*"),
        ("BrewRequest", "ingredients", "minItems", 0),
        ("BrewRequest", "ingredients", "maxItems", 6),
    )
    for model, field, constraint, value in mutations:
        changed = deepcopy(source)
        changed["components"]["schemas"][model]["properties"][field][constraint] = value
        assert canonical_schema(schema, changed) != original
    for key, value in (("required", ["name"]), ("additionalProperties", True)):
        changed = deepcopy(source)
        changed["components"]["schemas"]["BrewRequest"][key] = value
        assert canonical_schema(schema, changed) != original


def test_schema_comparison_only_equates_exclusive_unions() -> None:
    for alternatives in (
        [{"type": "string"}, {"type": "integer"}],
        [
            {
                "type": "object",
                "required": ["outcome"],
                "properties": {"outcome": {"const": "explosion"}},
            },
            {
                "type": "object",
                "required": ["outcome"],
                "properties": {"outcome": {"enum": ["amplified", "merged"]}},
            },
        ],
    ):
        assert canonical_schema({"oneOf": alternatives}, {}) == canonical_schema(
            {"anyOf": alternatives[::-1]}, {}
        )
    overlapping = [
        {"type": "integer", "minimum": 1},
        {"type": "integer", "maximum": 10},
    ]
    assert canonical_schema({"oneOf": overlapping}, {}) != canonical_schema(
        {"anyOf": overlapping}, {}
    )
    numeric_overlap = [{"type": "integer"}, {"type": "number"}]
    assert canonical_schema({"oneOf": numeric_overlap}, {}) != canonical_schema(
        {"anyOf": numeric_overlap}, {}
    )
