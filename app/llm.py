"""Тонкая обёртка над OpenAI-совместимым API с учётом причуд gpt-6-luna."""

from __future__ import annotations

import json
from typing import Dict, List

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from .config import Settings


class LLMError(RuntimeError):
    """Ошибка обращения к LLM, пригодная для показа пользователю."""


class LLMResponseError(LLMError):
    """Ответ модели не является валидным JSON."""


class LLMClient:
    def __init__(self, settings: Settings):
        self._s = settings
        self._client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.request_timeout,
        )

    def complete_json(self, messages: List[Dict[str, str]]) -> dict:
        """Вызвать модель в JSON-режиме и вернуть разобранный объект."""
        try:
            resp = self._client.chat.completions.create(
                model=self._s.model,
                messages=messages,
                response_format={"type": "json_object"},
                extra_body={
                    # Семейство gpt-6 не принимает max_tokens — только эти два поля.
                    "max_completion_tokens": self._s.max_completion_tokens,
                    "reasoning_effort": self._s.reasoning_effort,
                },
            )
        except AuthenticationError:
            raise LLMError("Ошибка авторизации: проверьте OPENAI_API_KEY.")
        except RateLimitError:
            raise LLMError("Превышен лимит запросов к API. Повторите позже.")
        except APITimeoutError:
            raise LLMError("Таймаут запроса к API.")
        except APIConnectionError:
            raise LLMError("Нет связи с API. Проверьте сеть и OPENAI_BASE_URL.")
        except APIError as e:
            raise LLMError(f"Ошибка API: {getattr(e, 'message', str(e))}")

        content = (resp.choices[0].message.content or "").strip()
        if not content:
            raise LLMResponseError("Модель вернула пустой ответ.")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            raise LLMResponseError("Модель вернула невалидный JSON.")
        if not isinstance(parsed, dict):
            raise LLMResponseError("Модель вернула не JSON-объект.")
        return parsed
