"""Заглушки внешних зависимостей для тестов"""

import asyncio


class FakePool:
    """Пул вместо asyncpg, отдаёт версию, падает с заданной ошибкой или отвечает с задержкой"""

    def __init__(
        self, version: str = "17.0", error: Exception | None = None, delay: float = 0
    ) -> None:
        self.version = version
        self.error = error
        self.delay = delay

    async def fetchval(self, query: str) -> str:
        """Ответить как Postgres на SHOW server_version"""
        await asyncio.sleep(self.delay)
        if self.error is not None:
            raise self.error
        return self.version
