"""Проверка реальных ответов по исходному OpenAPI с разрешением локальных $ref."""

from pathlib import Path

import yaml
from httpx2 import Response
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

CONTRACT_PATH = Path(__file__).resolve().parents[1] / "openapi.yaml"


def assert_response_matches_contract(
    response: Response, *, path: str, method: str = "get", status: int = 200
) -> None:
    contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    uri = "urn:potion-lab:contract"
    resource = Resource.from_contents(contract, default_specification=DRAFT202012)
    registry = Registry().with_resource(uri, resource)
    escaped = path.replace("~", "~0").replace("/", "~1")
    pointer = (
        f"{uri}#/paths/{escaped}/{method}/responses/{status}"
        "/content/application~1json/schema"
    )
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/json")
    Draft202012Validator({"$ref": pointer}, registry=registry).validate(response.json())
