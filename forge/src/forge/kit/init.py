"""FORGE init: онбординг проекта одной командой.

Создаёт только недостающие файлы (по умолчанию ничего не перезаписывает):
- `.github/workflows/forge-ci.yml` — CI под стек проекта (через `ci.generate`);
- `.forge-suppress.json` — пустой список подавлений с подсказкой;

и возвращает список следующих команд. Ничего не запускает и не коммитит.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

_SUPPRESS_STUB = "[]\n"


def init_project(root: str | Path, ci: bool = True, suppress: bool = True,
                 force: bool = False) -> dict[str, Any]:
    """Готовит проект к работе с FORGE. Возвращает что создано/пропущено."""
    base = Path(root)
    if not base.is_dir():
        return {"ok": False, "error": f"не директория: {base}"}
    created: list[str] = []
    skipped: list[str] = []
    problems: list[str] = []

    if suppress:
        sp = base / ".forge-suppress.json"
        if sp.exists() and not force:
            skipped.append(str(sp.name))
        else:
            try:
                sp.write_text(_SUPPRESS_STUB, encoding="utf-8")
                created.append(str(sp.name))
            except OSError as e:
                problems.append(f"{sp.name}: {e}")

    if ci:
        from forge.kit.ci import generate_ci
        res = generate_ci(base, force=force)
        if res.get("ok"):
            created.append(str(Path(res["path"]).name))
        elif res.get("exists"):
            skipped.append("forge-ci.yml")
        else:
            problems.append(res.get("error", "ci: не удалось сгенерировать"))

    return {
        "ok": not problems,
        "root": str(base),
        "created": created,
        "skipped": skipped,
        "problems": problems,
        "next": [
            f'forge audit "{base}" --min-score 80',
            f'forge test "{base}"',
            f'forge pipe run "{base}"',
        ],
    }
