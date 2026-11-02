"""Валидация входа и анализ полноты данных."""

from __future__ import annotations

import json
from typing import List, Tuple

from pydantic import ValidationError

from .schema import ProductInput


class InputError(ValueError):
    """Некорректный или неполный до непригодности вход."""


def parse_product_json(raw: str) -> ProductInput:
    """Разобрать JSON-строку в ProductInput с понятными ошибками."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise InputError(f"Некорректный JSON: {e.msg} (строка {e.lineno}, позиция {e.colno})")
    return parse_product_obj(data)


def parse_product_obj(data) -> ProductInput:
    if not isinstance(data, dict):
        raise InputError("Ожидался JSON-объект с данными о товаре")
    try:
        return ProductInput.model_validate(data)
    except ValidationError as e:
        msgs = "; ".join(err.get("msg", "ошибка") for err in e.errors())
        raise InputError(f"Данные не прошли валидацию: {msgs}")


# Базовый набор полей, который ожидаешь увидеть в карточке КИП. Их отсутствие —
# не ошибка, а повод подсветить контент-менеджеру («данных нет»).
RECOMMENDED_FIELDS = ["manufacturer", "specs", "description"]


def analyze_completeness(product: ProductInput) -> Tuple[List[str], List[str]]:
    """Вернуть (предупреждения, список отсутствующих полей)."""
    warnings: List[str] = []
    missing: List[str] = []

    if not product.manufacturer.strip():
        missing.append("manufacturer")
        warnings.append("Не указан производитель — в карточке проставлено «данных нет».")
    if not product.specs:
        missing.append("specs")
        warnings.append("Не переданы технические характеристики — список будет пустым.")
    if not product.description.strip():
        missing.append("description")
        warnings.append("Нет текстового описания/паспорта — текст построен только по названию и specs.")

    return warnings, missing
