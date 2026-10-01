"""Контракты ответов API на Pydantic"""

from enum import StrEnum

from pydantic import BaseModel


class HealthStatus(StrEnum):
    """Статус приложения или отдельной зависимости"""

    OK = "ok"
    FAIL = "fail"


class LivenessResponse(BaseModel):
    """Ответ /healthz"""

    status: HealthStatus


class VersionResponse(BaseModel):
    """Ответ /api/v1/version"""

    version: str


class ComponentHealth(BaseModel):
    """Состояние одной зависимости, её версия и время ответа"""

    status: HealthStatus
    version: str | None = None
    latency_ms: float
    error: str | None = None


class HealthResponse(BaseModel):
    """Ответ /api/v1/health с общим статусом и состоянием каждой зависимости"""

    status: HealthStatus
    components: dict[str, ComponentHealth]
