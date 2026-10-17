"""FORGE refactor API: единая точка входа для CLI, MCP и оконного режима."""
from __future__ import annotations

import json as _json
from pathlib import Path
from typing import Any

from forge.refactor.clean_code import analyze_dir, analyze_file


def inspect(path: str | Path) -> dict[str, Any]:
    """Анализировать файл или директорию на проблемы чистого кода."""
    p = Path(path)
    if p.is_dir():
        return analyze_dir(p)
    return analyze_file(p)


def suggest(path: str | Path) -> dict[str, Any]:
    """То же, что inspect, но только читаемые рекомендации (без сырых данных)."""
    res = inspect(path)
    if not res.get("ok", True):
        return res
    if "files_analyzed" in res:
        # директория
        out = {"root": res["root"], "total_issues": res["total_issues"],
               "score": res.get("score", 100), "files": res["files"]}
        recommendations = []
        for f in res["files_analyzed"]:
            if f.get("issues"):
                recommendations.append({"file": f["file"], "issues": f["issues"]})
        out["files_with_issues"] = recommendations
        return out
    return {"file": res["file"], "issues": res.get("issues", []),
            "total": res.get("total", 0), "score": res.get("score", 100)}
