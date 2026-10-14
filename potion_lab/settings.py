"""Настройки экземпляра приложения без автоматического чтения .env."""

import os
from collections.abc import Mapping
from dataclasses import dataclass

LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "potion-lab"
    app_author: str = "Не указан"
    app_port: int = 8000
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        for label, value in (
            ("APP_NAME", self.app_name),
            ("APP_AUTHOR", self.app_author),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label}: требуется непустая строка.")
        if type(self.app_port) is not int or not 1 <= self.app_port <= 65535:
            raise ValueError("APP_PORT: требуется целое число от 1 до 65535.")
        if not isinstance(self.log_level, str):
            raise ValueError("LOG_LEVEL: требуется название уровня логирования.")
        level = self.log_level.strip().upper()
        if level not in LOG_LEVELS:
            raise ValueError(
                "LOG_LEVEL: допустимы DEBUG, INFO, WARNING, ERROR, CRITICAL."
            )
        object.__setattr__(self, "log_level", level)


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    source = os.environ if environ is None else environ
    try:
        port = int(source.get("APP_PORT", "8000"))
    except ValueError:
        raise ValueError("APP_PORT: требуется целое число от 1 до 65535.") from None
    return Settings(
        app_name=source.get("APP_NAME", "potion-lab"),
        app_author=source.get("APP_AUTHOR", "Не указан"),
        app_port=port,
        log_level=source.get("LOG_LEVEL", "INFO"),
    )
