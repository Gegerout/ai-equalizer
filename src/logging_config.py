"""Структурированные логи в формате JSON, одна строка на одну запись

request_id живёт в ContextVar, middleware ставит его на время запроса,
и все логи одного запроса связываются одним id
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# Стандартные поля LogRecord, всё остальное пришло через extra и попадёт в JSON
_RECORD_ATTRS = set(vars(logging.makeLogRecord({}))) | {"message", "color_message"}


class JsonFormatter(logging.Formatter):
    """Форматирует запись лога в JSON"""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": request_id_var.get(),
            "msg": record.getMessage(),
        }
        payload.update({k: v for k, v in vars(record).items() if k not in _RECORD_ATTRS})
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: str) -> None:
    """Настроить корневой логгер и перевести логи uvicorn в тот же формат"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level.upper(), handlers=[handler], force=True)
    logging.getLogger("uvicorn").handlers.clear()
    logging.getLogger("uvicorn").propagate = True
    # Access лог uvicorn дублирует наш middleware, который пишет ещё и request_id
    logging.getLogger("uvicorn.access").disabled = True
