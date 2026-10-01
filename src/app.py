"""Точка сборки приложения FastAPI"""

import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Request, Response

from src.api import healthz, v1
from src.config import get_app_version, get_settings
from src.logging_config import request_id_var, setup_logging

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Создать пул соединений с Postgres при старте и закрыть при остановке"""
    settings = get_settings()
    # Пул с min_size 0 не подключается при старте, поэтому приложение поднимется и без БД,
    # а /api/v1/health покажет, что она недоступна
    app.state.db_pool = await asyncpg.create_pool(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password.get_secret_value(),
        database=settings.postgres_db,
        min_size=0,
    )
    log.info("application started", extra={"version": app.version})
    yield
    await app.state.db_pool.close()
    log.info("application stopped")


async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Выдать запросу request_id и залогировать метод, путь, статус и длительность"""
    request_id = uuid.uuid4().hex
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    try:
        response = await call_next(request)
        log.info(
            "request handled",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
            },
        )
    except Exception:
        # Access лог uvicorn выключен, без этой записи упавший запрос пропадёт из логов
        log.exception(
            "request failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
            },
        )
        raise
    finally:
        request_id_var.reset(token)
    response.headers["X-Request-ID"] = request_id
    return response


def create_app() -> FastAPI:
    """Собрать приложение, подключить логи, роуты и middleware"""
    setup_logging(get_settings().log_level)
    app = FastAPI(title="ai-equalizer", version=get_app_version(), lifespan=lifespan)
    app.middleware("http")(log_requests)
    app.include_router(healthz.router)
    app.include_router(v1.router)
    return app


app = create_app()
