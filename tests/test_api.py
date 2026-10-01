"""Тесты трёх эндпоинтов через HTTP"""

import json
import logging
import tomllib
from pathlib import Path

import pytest

from src.app import app
from src.logging_config import JsonFormatter
from tests.fakes import FakePool

PYPROJECT_PATH = Path(__file__).resolve().parents[1] / "pyproject.toml"
PYPROJECT_VERSION = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))["project"]["version"]


def _json_logs(caplog: pytest.LogCaptureFixture) -> list[dict]:
    """Разобрать захваченные логи, каждая строка это один JSON"""
    return [json.loads(line) for line in caplog.text.splitlines()]


async def test_healthz_returns_ok_without_database(client) -> None:
    """GET /healthz отвечает 200 без обращения к БД и отдаёт request_id в заголовке"""
    response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert len(response.headers["X-Request-ID"]) == 32


async def test_version_comes_from_pyproject(client) -> None:
    """GET /api/v1/version отдаёт версию из pyproject.toml, ту же что в Swagger"""
    response = await client.get("/api/v1/version")

    assert response.status_code == 200
    assert response.json() == {"version": PYPROJECT_VERSION}
    assert app.version == PYPROJECT_VERSION


async def test_healthz_requests_are_logged_at_debug_level(client, caplog) -> None:
    """Запросы healthcheck пишутся на DEBUG, остальные на INFO"""
    caplog.set_level(logging.DEBUG)

    await client.get("/healthz")
    await client.get("/api/v1/version")

    levels = {r.path: r.levelname for r in caplog.records if r.msg == "request handled"}
    assert levels == {"/healthz": "DEBUG", "/api/v1/version": "INFO"}


async def test_health_returns_200_when_postgres_healthy(client, monkeypatch) -> None:
    """GET /api/v1/health отдаёт 200, версию БД и время ответа, если БД отвечает"""
    # client объявлен раньше monkeypatch, поэтому подмена откатится до остановки приложения,
    # и lifespan закроет настоящий пул, а не заглушку
    monkeypatch.setattr(app.state, "db_pool", FakePool(version="17.0"))

    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    postgres = body["components"]["postgres"]
    assert postgres["status"] == "ok"
    assert postgres["version"] == "17.0"
    assert postgres["latency_ms"] >= 0
    assert postgres["error"] is None


async def test_health_returns_503_when_postgres_unavailable(client) -> None:
    """GET /api/v1/health отдаёт 503 и имя ошибки, если БД недоступна"""
    # Здесь работает настоящий asyncpg, он стучится в закрытый порт из conftest
    response = await client.get("/api/v1/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "fail"
    postgres = body["components"]["postgres"]
    assert postgres["status"] == "fail"
    assert postgres["version"] is None
    assert postgres["error"] == "ConnectionRefusedError"


async def test_logs_of_one_request_share_request_id(client, monkeypatch, caplog) -> None:
    """Все логи запроса пишутся в JSON и связаны request_id из заголовка ответа"""
    # Захват логов pytest не знает про request_id, поэтому включаем наш формат
    caplog.handler.setFormatter(JsonFormatter())
    # Заглушка вместо закрытого порта, потому что на Python 3.11 coverage теряет строки,
    # выполненные после настоящей сетевой ошибки, и ветка 503 выглядела бы непокрытой
    monkeypatch.setattr(app.state, "db_pool", FakePool(error=ConnectionRefusedError()))

    response = await client.get("/api/v1/health")

    request_id = response.headers["X-Request-ID"]
    messages = [log["msg"] for log in _json_logs(caplog) if log["request_id"] == request_id]
    assert messages == ["postgres health check failed", "request handled"]


async def test_unexpected_error_is_logged_and_not_masked(client, monkeypatch, caplog) -> None:
    """Баг в коде не выдаётся за недоступную БД, а падает и попадает в лог с request_id"""
    caplog.handler.setFormatter(JsonFormatter())
    monkeypatch.setattr(app.state, "db_pool", FakePool(error=RuntimeError("bug")))

    with pytest.raises(RuntimeError, match="bug"):
        await client.get("/api/v1/health")

    failed = [log for log in _json_logs(caplog) if log["msg"] == "request failed"]
    assert len(failed) == 1
    assert failed[0]["level"] == "ERROR"
    assert failed[0]["path"] == "/api/v1/health"
    assert failed[0]["request_id"] != "-"
    assert "RuntimeError: bug" in failed[0]["exc_info"]
