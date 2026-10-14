from dataclasses import FrozenInstanceError

import pytest

from potion_lab.settings import Settings, load_settings

pytestmark = pytest.mark.unit


def test_defaults_do_not_read_dotenv(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("APP_NAME=DOTENV_SECRET\n", encoding="utf-8")
    for key in ("APP_NAME", "APP_AUTHOR", "APP_PORT", "LOG_LEVEL"):
        monkeypatch.delenv(key, raising=False)
    assert load_settings() == Settings()
    assert Settings().app_author == "Не указан"
    assert Settings().app_port == 8000
    assert Settings().log_level == "INFO"


def test_valid_settings_and_immutability() -> None:
    for port in (1, 65535):
        selected = load_settings(
            {
                "APP_NAME": "Лаборатория",
                "APP_AUTHOR": "Автор",
                "APP_PORT": str(port),
                "LOG_LEVEL": "debug",
            }
        )
        assert selected == Settings("Лаборатория", "Автор", port, "DEBUG")
        with pytest.raises(FrozenInstanceError):
            selected.app_port = 8000
    for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        assert Settings(log_level=level.lower()).log_level == level


def test_invalid_settings_have_safe_reasons() -> None:
    cases = {
        "APP_NAME": ("", " \t\n"),
        "APP_AUTHOR": ("", " \t\n"),
        "APP_PORT": ("", "0", "65536", "1.5", "true", "nan", "inf", "PORT_SECRET"),
        "LOG_LEVEL": ("", " ", "LEVEL_SECRET"),
    }
    for key, values in cases.items():
        for value in values:
            with pytest.raises(ValueError, match=key) as error:
                load_settings({key: value})
            assert "SECRET" not in str(error.value)
    for value in (True, 1.5, 0, 65536):
        with pytest.raises(ValueError, match="APP_PORT"):
            Settings(app_port=value)
