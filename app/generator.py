"""Оркестрация: вход → проверки → LLM → сборка карточки товара."""

from __future__ import annotations

from typing import List, Optional

from .config import Settings, load_settings
from .factcheck import check_fabrication
from .llm import LLMClient, LLMResponseError
from .prompt import SYSTEM_PROMPT, build_retry_feedback, build_user_message
from .schema import NO_DATA, Characteristic, ProductCard, ProductInput
from .validation import analyze_completeness

TITLE_MAX = 70
DESC_MIN, DESC_MAX = 800, 1200


def _characteristics_from_input(product: ProductInput) -> List[Characteristic]:
    """Список характеристик строим ДЕТЕРМИНИРОВАННО из входа — без участия LLM.
    Это гарантирует, что в характеристиках не окажется выдуманных значений."""
    if not product.specs:
        return [Characteristic(name="Характеристики", value=NO_DATA)]
    return [
        Characteristic(name=k, value=(v.strip() or NO_DATA))
        for k, v in product.specs.items()
    ]


def _validate_card_fields(data: dict) -> List[str]:
    """Проверить структуру и лимиты ответа LLM. Вернуть список проблем."""
    problems: List[str] = []
    for key in ("seo_title", "seo_description", "search_queries", "commercial_block"):
        if key not in data:
            problems.append(f"отсутствует поле {key}")

    title = str(data.get("seo_title", "")).strip()
    if title and len(title) > TITLE_MAX:
        problems.append(f"seo_title длиннее {TITLE_MAX} символов ({len(title)})")

    desc = str(data.get("seo_description", "")).strip()
    if desc and not (DESC_MIN <= len(desc) <= DESC_MAX):
        problems.append(
            f"seo_description вне диапазона {DESC_MIN}–{DESC_MAX} символов ({len(desc)})"
        )

    queries = data.get("search_queries", [])
    if isinstance(queries, list) and not (3 <= len(queries) <= 5):
        problems.append("search_queries должно быть 3–5 штук")

    return problems


class CardGenerator:
    def __init__(self, settings: Optional[Settings] = None):
        self._settings = settings or load_settings()
        self._llm = LLMClient(self._settings)

    def generate(self, product: ProductInput) -> ProductCard:
        warnings, missing = analyze_completeness(product)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_message(product, missing)},
        ]

        data = self._llm.complete_json(messages)
        problems = _validate_card_fields(data)

        # Одна корректирующая попытка, если нарушены лимиты длины/количества.
        if problems:
            messages.append({"role": "assistant", "content": _as_text(data)})
            messages.append({"role": "user", "content": build_retry_feedback(problems)})
            try:
                retry = self._llm.complete_json(messages)
                retry_problems = _validate_card_fields(retry)
                if len(retry_problems) <= len(problems):
                    data, problems = retry, retry_problems
            except LLMResponseError:
                pass  # оставляем первый ответ, ниже подрежем/пометим

        title = str(data.get("seo_title", "")).strip()
        if len(title) > TITLE_MAX:
            title = title[:TITLE_MAX].rstrip(" ,.–-")
            warnings.append("SEO-заголовок был длиннее 70 символов и подрезан.")

        desc = str(data.get("seo_description", "")).strip()
        if desc and not (DESC_MIN <= len(desc) <= DESC_MAX):
            warnings.append(
                f"SEO-описание получилось {len(desc)} символов (целевой диапазон {DESC_MIN}–{DESC_MAX})."
            )

        raw_queries = data.get("search_queries", [])
        if not isinstance(raw_queries, list):
            raw_queries = []
        queries = [str(q).strip() for q in raw_queries if str(q).strip()]
        commercial = str(data.get("commercial_block", "")).strip()

        # Эвристическая проверка на выдуманные числа в сгенерированном тексте.
        warnings += check_fabrication(desc, product)
        warnings += check_fabrication(commercial, product)

        return ProductCard(
            seo_title=title or NO_DATA,
            seo_description=desc or NO_DATA,
            characteristics=_characteristics_from_input(product),
            search_queries=queries,
            commercial_block=commercial or NO_DATA,
            warnings=warnings,
        )


def _as_text(data: dict) -> str:
    import json

    return json.dumps(data, ensure_ascii=False)
