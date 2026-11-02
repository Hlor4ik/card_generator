"""Эвристическая проверка: не появились ли в тексте числовые характеристики,
которых нет во входных данных. Это второй рубеж против галлюцинаций —
дополняет жёсткий промпт, но не заменяет вычитку человеком."""

from __future__ import annotations

import re
from typing import List

from .schema import ProductInput

# Единицы измерения, типичные для КИП. Токен «число + единица» считаем
# технической характеристикой, которую нельзя выдумывать.
_UNITS = [
    "МПа", "кПа", "гПа", "Па", "бар", "мбар", "кгс/см²", "кгс/см2",
    "мм рт.ст.", "мм", "см", "°C", "°С", "К",
    "кВ", "мВ", "В", "мА", "кА", "А",
    "кГц", "МГц", "Гц", "Вт", "кВт",
    "кг", "г", "%",
]
_UNITS_RE = "|".join(re.escape(u) for u in sorted(_UNITS, key=len, reverse=True))

# Число с единицей: "1,6 МПа", "4–20 мА", "100 мм".
_MEASURE_RE = re.compile(rf"(\d[\d.,–\-\s]*?)\s?(?:{_UNITS_RE})", re.IGNORECASE)
# Резьбы и типоразмеры: G1/2, M20x1.5, Rc1/4.
_THREAD_RE = re.compile(r"\b(?:G|M|R|Rc|Rp|K)\s?\d+(?:[/x.,]\d+)?\b", re.IGNORECASE)
# Класс защиты: IP65.
_IP_RE = re.compile(r"\bIP\s?\d{2}\b", re.IGNORECASE)


def _norm(s: str) -> str:
    """Нормализовать для сравнения: нижний регистр, убрать пробелы и дефисы."""
    return re.sub(r"[\s–—\-]", "", s.lower())


def _digits(s: str) -> List[str]:
    """Все числовые ядра строки (без единиц), нормализованные."""
    return [_norm(m) for m in re.findall(r"\d[\d.,]*", s)]


def check_fabrication(text: str, product: ProductInput) -> List[str]:
    """Вернуть предупреждения о числах/типоразмерах из text, которых нет во входе."""
    source = " ".join(
        [product.name, product.manufacturer, product.description, *product.specs.values()]
    )
    source_norm = _norm(source)
    source_digits = set(_digits(source))

    suspects: List[str] = []
    seen: set[str] = set()

    for regex in (_MEASURE_RE, _THREAD_RE, _IP_RE):
        for match in regex.finditer(text):
            token = match.group(0).strip()
            key = _norm(token)
            if not key or key in seen:
                continue
            # Токен считаем подтверждённым, если он целиком есть во входе
            # либо все его числовые ядра присутствуют во входе.
            if key in source_norm:
                continue
            toks = _digits(token)
            if toks and all(d in source_digits for d in toks):
                continue
            seen.add(key)
            suspects.append(token)

    if suspects:
        uniq = ", ".join(f"«{s}»" for s in suspects)
        return [
            "Проверьте вручную: в тексте есть числовые значения, которых нет во "
            f"входных данных ({uniq}). Возможна выдуманная характеристика."
        ]
    return []
