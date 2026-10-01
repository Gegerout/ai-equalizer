"""Проверка живости процесса для Docker и оркестраторов

Живёт вне /api/v1, потому что это не часть версионируемого API, а служебный
эндпоинт инфраструктуры, он не меняется при выходе v2
"""

from fastapi import APIRouter

from src.schemas import HealthStatus, LivenessResponse

router = APIRouter()


@router.get("/healthz")
async def healthz() -> LivenessResponse:
    """Вернуть ok, если процесс жив, без внешних вызовов"""
    return LivenessResponse(status=HealthStatus.OK)
