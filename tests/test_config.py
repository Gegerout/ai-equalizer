"""Тесты настроек, обязательного пароля и проверки значений"""

import pytest
from pydantic import ValidationError

from src.config import Settings


def test_settings_require_postgres_password(monkeypatch) -> None:
    """Без пароля приложение не стартует, значения по умолчанию у него нет"""
    monkeypatch.delenv("POSTGRES_PASSWORD")

    # Локальный .env отключён, иначе пароль подтянулся бы из него
    with pytest.raises(ValidationError, match="postgres_password"):
        Settings(_env_file=None)


@pytest.mark.parametrize("value", ["0", "-1"])
def test_settings_reject_non_positive_health_timeout(monkeypatch, value) -> None:
    """Таймаут ноль или меньше отклоняется при старте"""
    monkeypatch.setenv("HEALTH_TIMEOUT", value)

    with pytest.raises(ValidationError, match="health_timeout"):
        Settings(_env_file=None)


def test_settings_hide_password(monkeypatch) -> None:
    """Пароль не виден при выводе настроек, но доступен явным вызовом"""
    monkeypatch.setenv("POSTGRES_PASSWORD", "s3cret")

    settings = Settings(_env_file=None)

    assert "s3cret" not in repr(settings)
    assert settings.postgres_password.get_secret_value() == "s3cret"
