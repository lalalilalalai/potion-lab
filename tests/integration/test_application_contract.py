import logging
from copy import deepcopy

import pytest
import yaml
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from potion_lab.application import create_app
from potion_lab.settings import Settings
from tests.contract import CONTRACT_PATH, operation_signature, operations

pytestmark = pytest.mark.integration


def test_openapi_contract() -> None:
    source = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    app = create_app(Settings())
    with TestClient(app) as client:
        published = client.get("/openapi.json")
        docs = client.get("/docs")
        assert client.get("/info").status_code == 404
    assert published.status_code == 200
    assert published.json() == source
    assert app.openapi_version == source["openapi"]
    assert app.version == source["info"]["version"]
    assert source["servers"][0]["url"] == "/"
    assert docs.status_code == 200
    assert "text/html" in docs.headers["content-type"]
    assert "SwaggerUIBundle" in docs.text
    assert "url: '/openapi.json'" in docs.text
    actual_routes = {
        (route.path, method.lower())
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    }
    assert actual_routes == operations(source)
    generated = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        routes=app.routes,
    )
    assert operations(generated) == operations(source)
    for path, method in operations(source):
        assert operation_signature(generated, path, method) == operation_signature(
            source, path, method
        ), (path, method)


def test_application_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    handlers = tuple(logging.getLogger().handlers)
    logger_level = logging.getLogger("potion_lab").level
    first_settings = Settings("Первый", "Автор первого", 8101, "DEBUG")
    first = create_app(first_settings)
    monkeypatch.setenv("APP_NAME", "Второй")
    monkeypatch.setenv("APP_AUTHOR", "Автор второго")
    monkeypatch.setenv("APP_PORT", "8102")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    second = create_app()
    second_settings = deepcopy(second.state.settings)
    monkeypatch.setenv("APP_NAME", "Изменено")
    monkeypatch.setenv("APP_PORT", "INVALID_SECRET")
    monkeypatch.setenv("LOG_LEVEL", "INVALID_SECRET")

    def unexpected_settings_read():
        raise AssertionError("Настройки перечитаны после создания приложения")

    monkeypatch.setattr(
        "potion_lab.application.load_settings", unexpected_settings_read
    )
    assert create_app(first_settings).state.settings is first_settings
    with TestClient(first) as first_client, TestClient(second) as second_client:
        for client, name in ((first_client, "Первый"), (second_client, "Второй")):
            assert client.get("/health").json() == {"status": "ok"}
            assert client.get("/version").json() == {"version": first.version}
            assert name in client.get("/docs").text
        assert (
            first_client.get("/openapi.json").json()
            == second_client.get("/openapi.json").json()
        )
    assert first.state.settings is first_settings
    assert (
        second.state.settings
        == second_settings
        == Settings("Второй", "Автор второго", 8102, "WARNING")
    )
    assert first.title == "Первый"
    assert second.title == "Второй"
    modified = first.openapi()
    modified["info"]["version"] = "CHANGED"
    assert first.openapi()["info"]["version"] == first.version
    assert second.openapi()["info"]["version"] == second.version
    assert tuple(logging.getLogger().handlers) == handlers
    assert logging.getLogger("potion_lab").level == logger_level
