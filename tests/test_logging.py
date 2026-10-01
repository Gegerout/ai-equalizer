"""Тесты JSON форматтера логов"""

import json
import logging
import sys

from src.logging_config import JsonFormatter


def test_json_formatter_puts_extra_fields_into_json() -> None:
    """Поля из extra становятся ключами JSON, служебные поля LogRecord не попадают"""
    record = logging.makeLogRecord(
        {
            "name": "src.test",
            "levelname": "INFO",
            "msg": "user %s",
            "args": ("created",),
            "status": 201,
        }
    )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "src.test"
    assert payload["msg"] == "user created"
    assert payload["status"] == 201
    assert payload["request_id"] == "-"
    assert "args" not in payload


def test_json_formatter_keeps_traceback_on_one_line() -> None:
    """Traceback попадает в JSON, а запись остаётся одной строкой"""
    try:
        raise ValueError("broken")
    except ValueError:
        record = logging.makeLogRecord({"msg": "failed", "exc_info": sys.exc_info()})

    line = JsonFormatter().format(record)

    assert "\n" not in line
    assert "ValueError: broken" in json.loads(line)["exc_info"]
