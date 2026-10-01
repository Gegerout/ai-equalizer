"""Общие фикстуры тестов"""

import os
from collections.abc import AsyncIterator

# Окружение задаётся до импорта src.app, потому что приложение собирается при импорте
# Порт 59999 заведомо закрыт, поэтому сценарий с недоступной БД повторяется на любой машине
os.environ["POSTGRES_HOST"] = "127.0.0.1"
os.environ["POSTGRES_PORT"] = "59999"
os.environ["POSTGRES_USER"] = "test"
os.environ["POSTGRES_PASSWORD"] = "test"
os.environ["POSTGRES_DB"] = "test"
os.environ["HEALTH_TIMEOUT"] = "1"

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from src.app import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """HTTP клиент приложения, который запускает lifespan с пулом БД"""
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http:
            yield http
