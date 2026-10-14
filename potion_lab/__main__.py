"""Запуск: python -m potion_lab из активного виртуального окружения."""

import logging

import uvicorn

from potion_lab.application import create_app
from potion_lab.logging_config import configure_logging
from potion_lab.settings import load_settings


def main() -> None:
    try:
        settings = load_settings()
    except ValueError as error:
        configure_logging("INFO")
        logging.getLogger("potion_lab").critical("Запуск отклонён: %s", error)
        raise SystemExit(2) from None
    configure_logging(settings.log_level)
    app = create_app(settings)
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=settings.app_port,
        log_level=settings.log_level.lower(),
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
