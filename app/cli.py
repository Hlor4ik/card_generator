"""CLI: python -m app.cli <file.json ...> [--format md|json|text] [--out DIR]

Можно подать несколько файлов или '-' для чтения JSON из stdin."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import ConfigError
from .generator import CardGenerator
from .llm import LLMError
from .render import to_json, to_markdown, to_text
from .validation import InputError, parse_product_json

_RENDERERS = {"md": to_markdown, "json": to_json, "text": to_text}
_EXT = {"md": ".md", "json": ".json", "text": ".txt"}


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Генератор карточек товара КИП")
    parser.add_argument("inputs", nargs="+", help="JSON-файлы с товарами или '-' для stdin")
    parser.add_argument("--format", choices=_RENDERERS, default="md", help="формат вывода")
    parser.add_argument("--out", help="каталог для сохранения результатов (иначе — в stdout)")
    args = parser.parse_args(argv)

    try:
        generator = CardGenerator()
    except ConfigError as e:
        print(f"Ошибка конфигурации: {e}", file=sys.stderr)
        return 2

    render = _RENDERERS[args.format]
    out_dir = Path(args.out) if args.out else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    exit_code = 0
    for path in args.inputs:
        try:
            product = parse_product_json(_read(path))
            card = generator.generate(product)
        except FileNotFoundError:
            print(f"[{path}] файл не найден", file=sys.stderr)
            exit_code = 1
            continue
        except InputError as e:
            print(f"[{path}] {e}", file=sys.stderr)
            exit_code = 1
            continue
        except LLMError as e:
            print(f"[{path}] {e}", file=sys.stderr)
            exit_code = 1
            continue

        output = render(card)
        if out_dir:
            stem = "stdin" if path == "-" else Path(path).stem
            dest = out_dir / f"{stem}{_EXT[args.format]}"
            dest.write_text(output, encoding="utf-8")
            print(f"[{path}] → {dest}", file=sys.stderr)
        else:
            if len(args.inputs) > 1:
                print(f"\n===== {path} =====\n")
            print(output)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
