"""Конфигурация: читается из окружения / .env. Секреты в коде не хранятся."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Подхватываем .env из корня проекта (если есть). Реальные значения — только в .env,
# который добавлен в .gitignore.
load_dotenv()


class ConfigError(RuntimeError):
    """Отсутствует обязательная настройка."""


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model: str
    # Причуды семейства gpt-6-luna: только max_completion_tokens и reasoning_effort.
    max_completion_tokens: int = 4000
    reasoning_effort: str = "none"
    request_timeout: float = 60.0


def load_settings() -> Settings:
    """Собрать настройки из окружения. Кидает ConfigError, если нет ключа."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ConfigError(
            "Не задан OPENAI_API_KEY. Скопируйте .env.example в .env и впишите ключ."
        )
    return Settings(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip(),
        model=os.getenv("MODEL", "gpt-6-luna").strip(),
    )
