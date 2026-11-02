"""Веб-интерфейс: простая форма + JSON API.

Запуск: uvicorn app.web:app --reload
  GET  /            — HTML-форма (вставить JSON → получить карточку)
  POST /generate    — JSON на входе и выходе (для интеграций)
"""

from __future__ import annotations

import html
import json

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse

from .config import ConfigError
from .generator import CardGenerator
from .llm import LLMError
from .render import to_markdown
from .schema import ProductCard
from .validation import InputError, parse_product_json, parse_product_obj

app = FastAPI(title="AI-помощник: карточки товара КИП")

_SAMPLE = {
    "name": "Манометр показывающий DM 02",
    "manufacturer": "Манотомь",
    "specs": {
        "диапазон измерений": "0–1,6 МПа",
        "класс точности": "1,5",
        "присоединение": "G1/2",
        "диаметр корпуса": "100 мм",
    },
    "description": "Прибор предназначен для измерения избыточного давления...",
}


def _get_generator() -> CardGenerator:
    # Ленивая инициализация — чтобы форма открывалась даже без ключа.
    return CardGenerator()


def _page(body: str) -> str:
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Карточки товара КИП</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 820px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }}
  textarea {{ width: 100%; min-height: 240px; font-family: monospace; font-size: 13px; padding: .6rem; box-sizing: border-box; }}
  button {{ background: #2563eb; color: #fff; border: 0; padding: .6rem 1.2rem; border-radius: 6px; font-size: 15px; cursor: pointer; }}
  .card {{ background: #f7f7f8; border: 1px solid #e3e3e8; border-radius: 8px; padding: 1rem 1.4rem; margin-top: 1.5rem; }}
  .warn {{ color: #b45309; }}
  .err {{ background: #fef2f2; border-color: #fecaca; color: #b91c1c; }}
  pre {{ white-space: pre-wrap; word-wrap: break-word; }}
</style></head><body>
<h1>AI-помощник: карточка товара КИП</h1>
<p>Вставьте данные о приборе в формате JSON и нажмите «Сгенерировать».</p>
{body}
</body></html>"""


def _form(json_text: str) -> str:
    return f"""<form method="post" action="/">
  <textarea name="payload">{html.escape(json_text)}</textarea>
  <p><button type="submit">Сгенерировать карточку</button></p>
</form>"""


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    sample = json.dumps(_SAMPLE, ensure_ascii=False, indent=2)
    return HTMLResponse(_page(_form(sample)))


@app.post("/", response_class=HTMLResponse)
def submit(payload: str = Form("")) -> HTMLResponse:
    try:
        product = parse_product_json(payload)
        card = _get_generator().generate(product)
    except ConfigError as e:
        return HTMLResponse(_page(_form(payload) + _error(str(e))))
    except InputError as e:
        return HTMLResponse(_page(_form(payload) + _error(str(e))))
    except LLMError as e:
        return HTMLResponse(_page(_form(payload) + _error(str(e))))
    return HTMLResponse(_page(_form(payload) + _result(card)))


@app.post("/generate")
def generate_api(body: dict) -> JSONResponse:
    try:
        product = parse_product_obj(body)
        card = _get_generator().generate(product)
    except ConfigError as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    except InputError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except LLMError as e:
        return JSONResponse({"error": str(e)}, status_code=502)
    return JSONResponse(card.model_dump())


def _error(msg: str) -> str:
    return f'<div class="card err"><strong>Ошибка:</strong> {html.escape(msg)}</div>'


def _result(card: ProductCard) -> str:
    md = html.escape(to_markdown(card))
    return f'<div class="card"><pre>{md}</pre></div>'
