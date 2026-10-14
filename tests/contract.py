"""Проверка реальных ответов по исходному OpenAPI с разрешением локальных $ref."""

import json
from itertools import combinations
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
    response_spec = contract["paths"][path][method]["responses"][str(status)]
    pointer = f"{uri}#/paths/{escaped}/{method}/responses/{status}"
    if "$ref" in response_spec:
        pointer = uri + response_spec["$ref"]
    pointer += "/content/application~1json/schema"
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/json")
    Draft202012Validator({"$ref": pointer}, registry=registry).validate(response.json())


def resolve_reference(value: dict, document: dict) -> dict:
    while "$ref" in value:
        reference = value["$ref"]
        assert reference.startswith("#/"), reference
        target = document
        for token in reference[2:].split("/"):
            target = target[token.replace("~1", "/").replace("~0", "~")]
        value = {
            **target,
            **{key: item for key, item in value.items() if key != "$ref"},
        }
    return value


def _exclusive(left: dict, right: dict) -> bool:
    def types(schema: dict) -> set:
        value = schema.get("type", [])
        result = {value} if isinstance(value, str) else set(value)
        if "number" in result:
            result.add("integer")
        return result

    left_types, right_types = types(left), types(right)
    if left_types and right_types and left_types.isdisjoint(right_types):
        return True
    for field in set(left.get("required", [])) & set(right.get("required", [])):
        first = left.get("properties", {}).get(field, {})
        second = right.get("properties", {}).get(field, {})
        first_values = [first["const"]] if "const" in first else first.get("enum", [])
        second_values = (
            [second["const"]] if "const" in second else second.get("enum", [])
        )
        if first_values and second_values:
            first_set = {json.dumps(item, sort_keys=True) for item in first_values}
            second_set = {json.dumps(item, sort_keys=True) for item in second_values}
            if first_set.isdisjoint(second_set):
                return True
    return False


def canonical_schema(value, document: dict):
    """Разрешить $ref, сохранить ограничения и убрать только описательные метаданные."""
    if isinstance(value, list):
        return [canonical_schema(item, document) for item in value]
    if not isinstance(value, dict):
        return value
    value = resolve_reference(value, document)
    result = {}
    for key, item in value.items():
        if key in {"title", "description", "example", "examples", "$schema"}:
            continue
        if key == "additionalProperties" and item is True:
            continue
        if key == "properties":
            result[key] = {
                name: canonical_schema(schema, document)
                for name, schema in item.items()
            }
        elif key in {"required", "enum"}:
            result[key] = sorted(
                item, key=lambda entry: json.dumps(entry, sort_keys=True)
            )
        elif key in {"oneOf", "anyOf"}:
            variants = [canonical_schema(schema, document) for schema in item]
            if len(variants) > 1 and all(
                _exclusive(a, b) for a, b in combinations(variants, 2)
            ):
                key = "exclusiveUnion"
            result[key] = sorted(
                variants, key=lambda entry: json.dumps(entry, sort_keys=True)
            )
        else:
            result[key] = canonical_schema(item, document)
    if "enum" in result and len(result["enum"]) == 1:
        result["const"] = result.pop("enum")[0]
    return result


HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


def operations(document: dict) -> set[tuple[str, str]]:
    return {
        (path, method)
        for path, item in document["paths"].items()
        for method in item
        if method in HTTP_METHODS
    }


def operation_signature(document: dict, path: str, method: str) -> dict:
    path_item = document["paths"][path]
    operation = path_item[method]

    def content(container: dict) -> dict:
        container = resolve_reference(container, document)
        return {
            mime: canonical_schema(media.get("schema", {}), document)
            for mime, media in container.get("content", {}).items()
        }

    parameters = []
    for parameter in path_item.get("parameters", []) + operation.get("parameters", []):
        parameter = resolve_reference(parameter, document)
        parameters.append(
            {
                "name": parameter["name"],
                "in": parameter["in"],
                "required": parameter.get("required", False),
                "schema": canonical_schema(parameter.get("schema", {}), document),
            }
        )
    body = operation.get("requestBody")
    if body is not None:
        body = resolve_reference(body, document)
        body = {"required": body.get("required", False), "content": content(body)}
    return {
        "operationId": operation["operationId"],
        "parameters": sorted(parameters, key=lambda item: (item["in"], item["name"])),
        "requestBody": body,
        "responses": {
            str(status): content(response)
            for status, response in operation["responses"].items()
        },
    }
