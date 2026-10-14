import pytest
import yaml

from potion_lab.domain import list_ingredients
from tests.contract import CONTRACT_PATH

pytestmark = pytest.mark.unit


def test_catalog_matches_contract_and_cannot_be_changed_by_callers() -> None:
    contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    expected = contract["paths"]["/ingredients"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["example"]
    catalog = list_ingredients()
    assert [item.model_dump(mode="json") for item in catalog] == expected
    catalog[0].name = "Изменённое имя"
    catalog.clear()
    assert [item.model_dump(mode="json") for item in list_ingredients()] == expected
