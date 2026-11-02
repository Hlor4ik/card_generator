"""Схемы входных данных и результата (Pydantic)."""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field, field_validator

# Текст-заглушка для отсутствующих данных (требование ТЗ).
NO_DATA = "данных нет"


class ProductInput(BaseModel):
    """Входные данные о приборе. Единственный источник фактов для карточки."""

    name: str = Field(..., description="Название товара")
    manufacturer: str = Field(default="", description="Производитель")
    specs: Dict[str, str] = Field(default_factory=dict, description="Характеристики")
    description: str = Field(default="", description="Описание / фрагмент паспорта")

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Поле 'name' обязательно и не может быть пустым")
        return v.strip()

    @field_validator("specs", mode="before")
    @classmethod
    def _coerce_specs(cls, v):
        # Значения характеристик приводим к строкам (во входе бывают числа).
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("Поле 'specs' должно быть объектом (ключ-значение)")
        return {str(k): ("" if val is None else str(val)) for k, val in v.items()}


class Characteristic(BaseModel):
    name: str
    value: str


class ProductCard(BaseModel):
    """Черновик карточки товара — итоговый результат для контент-менеджера."""

    seo_title: str
    seo_description: str
    characteristics: List[Characteristic]
    search_queries: List[str]
    commercial_block: str
    # Что требует внимания человека: нехватка данных, превышение лимитов и т.п.
    warnings: List[str] = Field(default_factory=list)
