"""Рендер карточки в удобные для копирования форматы: Markdown, текст, JSON."""

from __future__ import annotations

from .schema import ProductCard


def to_markdown(card: ProductCard) -> str:
    lines = [
        f"# {card.seo_title}",
        "",
        "## SEO-описание",
        card.seo_description,
        "",
        "## Характеристики",
    ]
    for ch in card.characteristics:
        lines.append(f"- **{ch.name}:** {ch.value}")
    lines += ["", "## Поисковые запросы"]
    if card.search_queries:
        lines += [f"- {q}" for q in card.search_queries]
    else:
        lines.append("- данных нет")
    lines += ["", "## Блок для менеджера", card.commercial_block]
    if card.warnings:
        lines += ["", "## Требует внимания"]
        lines += [f"- {w}" for w in card.warnings]
    return "\n".join(lines) + "\n"


def to_text(card: ProductCard) -> str:
    """Плоский текст без markdown-разметки."""
    md = to_markdown(card)
    return md.replace("**", "").replace("# ", "").replace("#", "")


def to_json(card: ProductCard) -> str:
    return card.model_dump_json(indent=2)
