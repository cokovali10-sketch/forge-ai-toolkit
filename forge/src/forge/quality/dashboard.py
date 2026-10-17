"""FORGE quality: единый дашборд качества проекта + тренд + регресс-гейт.

Собирает в одну картину:
- чистый код (health score, число и типы замечаний),
- языки, которые найдены в проекте,
- (опционально) вердикт конвейера,
- историю замеров и направление тренда,
- и решает, «проходит ли» проект порог (`--min-score`) и не деградировал ли он
  (`--max-regression`).

FORGE ничего не выдумывает: метрики честные, гейт возвращает ненулевой код
выхода, если порог нарушен — это удобно в CI.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

_EXT_LANG = {
    ".py": "python", ".js": "javascript", ".mjs": "javascript",
    ".cjs": "javascript", ".ts": "typescript", ".tsx": "typescript",
    ".jsx": "javascript", ".rs": "rust", ".go": "go", ".cpp": "cpp",
    ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".c": "cpp", ".h": "cpp",
    ".java": "java", ".kt": "kotlin",
}


def _history_path(root: str, forge_root: str) -> Path:
    h = hashlib.sha1(str(Path(root).resolve()).encode("utf-8")).hexdigest()[:12]
    d = Path(forge_root) / "quality-history"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{h}.json"


def history(root: str, forge_root: str, limit: int = 20) -> list[dict[str, Any]]:
    p = _history_path(root, forge_root)
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return data if isinstance(data, list) else []


def record(snap: dict[str, Any], root: str, forge_root: str,
           keep: int = 100) -> None:
    hist = history(root, forge_root, limit=10 ** 9)
    hist.append(snap)
    p = _history_path(root, forge_root)
    p.write_text(json.dumps(hist[-keep:], ensure_ascii=False, indent=2),
                 encoding="utf-8")


def snapshot(root: str, forge_root: str, run_pipe: bool = False,
             stamp: str | None = None) -> dict[str, Any]:
    """Один замер качества проекта (без записи в историю)."""
    from forge.refactor.api import inspect as _inspect
    ins = _inspect(root)
    by_kind: dict[str, int] = {}
    by_sev: dict[str, int] = {}
    by_lang: dict[str, int] = {}
    for f in ins.get("files_analyzed", []):
        lang = _EXT_LANG.get(Path(f.get("file", "")).suffix.lower())
        if lang:
            by_lang[lang] = by_lang.get(lang, 0) + 1
        for it in f.get("issues", []):
            k = it.get("kind", "?")
            by_kind[k] = by_kind.get(k, 0) + 1
            s = it.get("severity", "low")
            by_sev[s] = by_sev.get(s, 0) + 1
    snap: dict[str, Any] = {
        "root": str(root),
        "score": ins.get("score", 100),
        "files": ins.get("files", 0),
        "issues": ins.get("total_issues", 0),
        "by_kind": dict(sorted(by_kind.items(), key=lambda kv: -kv[1])),
        "by_severity": by_sev,
        "langs": by_lang,
    }
    if stamp:
        snap["at"] = stamp
    if run_pipe:
        from forge.pipe.loop import run_loop
        snap["pipe"] = run_loop(root, forge_root, max_attempts=1,
                                auto_fix=False)["status"]
    return snap


def trend(root: str, forge_root: str, window: int = 20) -> dict[str, Any]:
    """Направление изменения score по последним замерам."""
    hist = history(root, forge_root, limit=window)
    if len(hist) < 2:
        return {"direction": "flat", "delta": 0, "samples": len(hist)}
    cur = hist[-1].get("score", 100)
    prev = hist[-2].get("score", 100)
    delta = cur - prev
    direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
    return {"direction": direction, "delta": delta, "samples": len(hist)}


def check(root: str, forge_root: str, min_score: float | None = None,
          max_regression: float | None = None, run_pipe: bool = False,
          save: bool = True) -> dict[str, Any]:
    """Замер + (опционально) запись в историю + решение по гейту."""
    tr_before = trend(root, forge_root)
    snap = snapshot(root, forge_root, run_pipe=run_pipe)
    reasons: list[str] = []
    if min_score is not None and snap["score"] < min_score:
        reasons.append(f"score {snap['score']:.0f} < минимум {min_score:.0f}")
    if max_regression is not None and tr_before["direction"] == "down":
        drop = -tr_before["delta"]
        if drop > max_regression:
            reasons.append(f"регресс -{drop:.0f} > допустимо {max_regression:.0f}")
    if save:
        record(snap, root, forge_root)
    tr_after = trend(root, forge_root)
    return {
        "ok": not reasons,
        "score": snap["score"],
        "files": snap["files"],
        "issues": snap["issues"],
        "by_kind": snap["by_kind"],
        "by_severity": snap["by_severity"],
        "langs": snap["langs"],
        "trend": tr_after,
        "reasons": reasons,
        **({"pipe": snap["pipe"]} if "pipe" in snap else {}),
    }
