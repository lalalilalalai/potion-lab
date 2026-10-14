import pytest

from potion_lab import __main__ as entrypoint

pytestmark = pytest.mark.unit


def test_startup_uses_settings_and_rejects_invalid_port(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    calls = []
    monkeypatch.setattr(entrypoint.uvicorn, "run", lambda app, **kw: calls.append(kw))
    monkeypatch.setattr(entrypoint, "configure_logging", lambda level: None)
    monkeypatch.setenv("APP_NAME", "Лаборатория")
    monkeypatch.setenv("APP_AUTHOR", "Автор")
    monkeypatch.setenv("APP_PORT", "8123")
    monkeypatch.setenv("LOG_LEVEL", "warning")
    entrypoint.main()
    assert calls == [
        {
            "host": "127.0.0.1",
            "port": 8123,
            "log_level": "warning",
            "log_config": None,
            "access_log": False,
        }
    ]
    monkeypatch.setenv("APP_PORT", "PORT_SECRET")
    with pytest.raises(SystemExit) as error:
        entrypoint.main()
    assert error.value.code == 2
    assert len(calls) == 1
    assert "APP_PORT" in caplog.text
    assert "PORT_SECRET" not in caplog.text
