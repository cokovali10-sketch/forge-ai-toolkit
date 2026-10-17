"""FORGE langs: общая база языковых модулей.

Каждый язык — detect/lint/test/scaffold с честными правилами:
- тулчейна нет = WARNING, а не FAIL (чужой комп не виноват);
- ошибка синтаксиса/типов = FAILED;
- всё через timeout, всё без зависимостей (только subprocess + stdlib).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from forge.core.result import ToolResult

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__",
             "build", "target", "out", ".gradle", ".idea", "dist"}


def which(prog: str) -> str:
    return shutil.which(prog) or ""


def collect(root: str | Path, exts: set[str], cap: int = 2000) -> list[Path]:
    """Файлы по расширениям. Лимит защищает от гигантских деревьев."""
    import os
    base = Path(root)
    out: list[Path] = []
    if not base.is_dir():
        return out
    for dirpath, dirnames, filenames in os.walk(base, onerror=lambda e: None):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            if Path(fn).suffix.lower() in exts:
                out.append(Path(dirpath) / fn)
                if len(out) >= cap:
                    return out
    return out


def run(cmd: list[str], cwd: str | Path, timeout: int = 300) -> dict[str, Any]:
    """Запуск тулчейна: {ok, code, log}. Нет бинаря = code 127, не исключение."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, cwd=str(cwd))
        out = (r.stdout or "") + (r.stderr or "")
        return {"ok": r.returncode == 0, "code": r.returncode,
                "log": out[-4000:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": 124, "log": f"[TIMEOUT {timeout}s]"}
    except FileNotFoundError:
        return {"ok": False, "code": 127, "log": f"missing: {cmd[0]}"}


def missing_tool(tool: str) -> ToolResult:
    return ToolResult(status="SUCCESS", result={"files_checked": 0},
                      warnings=[f"нет тулчейна ({tool}) — проверка пропущена"])


def write_tree(out: str | Path, files: dict[str, str]) -> list[str]:
    """Скаффолд: dict {relpath: content}. Возвращает созданные пути."""
    base = Path(out)
    made = []
    for rel, content in files.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        made.append(str(p.relative_to(base)))
    return made
