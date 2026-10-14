import logging

import pytest

from potion_lab.logging_config import configure_logging

pytestmark = pytest.mark.unit


def test_logging_threshold_does_not_duplicate_handlers(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger = logging.getLogger("potion_lab")
    handlers = tuple(logging.getLogger().handlers)
    with caplog.at_level(logging.DEBUG, logger="potion_lab"):
        configure_logging("WARNING")
        configure_logging("WARNING")
        for level in (
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ):
            logger.log(level, "Событие приложения")
    records = [record for record in caplog.records if record.name == "potion_lab"]
    assert [record.levelno for record in records] == [
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL,
    ]
    assert tuple(logging.getLogger().handlers) == handlers
