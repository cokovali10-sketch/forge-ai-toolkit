"""FORGE baseline: «держать линию» на реальных проектах.

Проблема: на большом чужом коде аудит сразу показывает сотни легаси-замечаний,
и честный гейт (`--min-score`) поднять невозможно. Решение — снять снимок
текущих проблем (baseline) и падать **только на новых**.

Отпечаток проблемы стабилен к сдвигу строк: это хэш
`область | правило | файл | нормализованный фрагмент`. Один и тот же дефект
(правило + файл + фрагмент) считается одним, вне зависимости от номера строки.

Только чтение: команда ничего не меняет в проекте (кроме записи самого файла
базлайна при `save`).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

DEFAULT_NAME = ".forge-baseline.json"
_SEV_ORDER = {"high": 0, "medium": 1, "low": 2}


def _rel(p: str, base: Path) -> str:
    p = str(p or "")
    if not p:
        return ""
    path = Path(p)
    if path.is_absolute():
        try:
            return str(path.relative_to(base.resolve())).replace("\\", "/")
        except ValueError:
            return p.replace("\\", "/")
    return p.replace("\\", "/")


def _norm(text: str) -> str:
    return " ".join(str(text or "").split())[:160].lower()


def _fingerprint(area: str, rule: str, file: str, context: str,
                 detail: str) -> str:
    seed = f"{area}|{rule}|{file}|{_norm(context) or _norm(detail)}"
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]


def _item(area: str, rule: str, file: str, line: int, severity: str,
          detail: str, context: str = "") -> dict[str, Any]:
    return {"area": area, "rule": rule, "file": file, "line": int(line or 0),
            "severity": severity if severity in _SEV_ORDER else "low",
            "detail": detail[:200],
            "fingerprint": _fingerprint(area, rule, file, context, detail)}


def collect(root: str | Path) -> dict[str, Any]:
    """Собирает все текущие проблемы проекта в список с отпечатками."""
    base = Path(root)
    if not base.is_dir():
        return {"ok": False, "error": f"не директория: {base}"}

    from forge.kit.deps import scan_deps
    from forge.kit.secrets import scan_secrets
    from forge.refactor.api import inspect

    items: list[dict[str, Any]] = []

    q = inspect(base)
    for f in q.get("files_analyzed", []) or []:
        rel = _rel(f.get("file", ""), base)
        for i in f.get("issues", []) or []:
            items.append(_item("quality", i.get("kind", "?"), rel,
                               i.get("line", 0), i.get("severity", "low"),
                               i.get("message", ""), i.get("context", "")))

    s = scan_secrets(base)
    for f in s.get("findings", []) or []:
        items.append(_item("secrets", f.get("kind", "?"), f.get("file", ""),
                           0, f.get("severity", "low"),
                           f"{f.get('kind')} @ {f.get('file')}",
                           f.get("preview", "")))

    d = scan_deps(base)
    for f in d.get("findings", []) or []:
        items.append(_item("deps", f.get("kind", "?"), f.get("file", ""),
                           0, f.get("severity", "low"),
                           f.get("detail", ""), f.get("kind", "")))

    return {"ok": True, "root": str(base), "count": len(items), "items": items}


def save(root: str | Path, path: str | Path | None = None) -> dict[str, Any]:
    """Снимает снимок текущих проблем в файл базлайна."""
    base = Path(root)
    snap = collect(base)
    if not snap.get("ok"):
        return snap
    target = Path(path) if path else base / DEFAULT_NAME
    paid = {"version": 1, "root": str(base), "count": snap["count"],
            "items": snap["items"]}
    try:
        target.write_text(json.dumps(paid, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    except OSError as e:
        return {"ok": False, "error": f"не записать {target}: {e}"}
    return {"ok": True, "path": str(target), "count": snap["count"]}


def load(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        return {"ok": False, "error": f"нет файла базлайна: {p}",
                "items": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        return {"ok": False, "error": f"битый базлайн: {e}", "items": []}
    return {"ok": True, "count": len(data.get("items", [])),
            "items": data.get("items", [])}


def diff(current: list[dict[str, Any]],
         baseline: list[dict[str, Any]]) -> dict[str, Any]:
    """Новые и закрытые проблемы относительно базлайна."""
    base_fp = {i.get("fingerprint") for i in baseline}
    cur: dict[str, dict[str, Any]] = {}
    for i in current:
        cur.setdefault(i.get("fingerprint"), i)
    new = [i for fp, i in cur.items() if fp not in base_fp]
    resolved = [i for i in baseline if i.get("fingerprint") not in cur]
    new.sort(key=lambda x: (_SEV_ORDER.get(x["severity"], 3), x["file"]))
    resolved.sort(key=lambda x: (_SEV_ORDER.get(x["severity"], 3), x["file"]))
    return {
        "new": new, "resolved": resolved,
        "new_counts": {sev: sum(1 for i in new if i["severity"] == sev)
                       for sev in ("high", "medium", "low")},
        "current_count": len(cur), "baseline_count": len(base_fp),
    }


def check(root: str | Path, path: str | Path | None = None,
          fail_on: str = "high") -> dict[str, Any]:
    """Сравнивает проект с базлайном. `fail_on`: high|medium|low|none."""
    base = Path(root)
    target = Path(path) if path else base / DEFAULT_NAME
    snap = collect(base)
    if not snap.get("ok"):
        return snap
    loaded = load(target)
    if not loaded.get("ok"):
        return {"ok": False, "error": loaded.get("error"),
                "baseline_missing": True}
    d = diff(snap["items"], loaded["items"])
    levels = {"none": -1, "high": 0, "medium": 1, "low": 2}
    threshold = levels.get(fail_on, 0)
    worst = min((_SEV_ORDER.get(i["severity"], 3) for i in d["new"]),
                default=9)
    ok = worst > threshold
    return {"ok": ok, "fail_on": fail_on, "baseline": str(target),
            "new": d["new"][:50], "new_counts": d["new_counts"],
            "resolved": len(d["resolved"]),
            "current_count": d["current_count"],
            "baseline_count": d["baseline_count"]}


def render_text(res: dict[str, Any]) -> str:
    if not res.get("ok") and res.get("baseline_missing"):
        return (f"baseline: {res.get('error')}\n"
                f"  сначала: forge baseline save <dir>")
    if not res.get("ok") and "new_counts" not in res:
        return f"baseline: {res.get('error')}"
    c = res.get("new_counts", {})
    head = "держит линию" if res.get("ok") else "ЕСТЬ НОВЫЕ ПРОБЛЕМЫ"
    lines = [f"FORGE baseline: {head} (порог: {res.get('fail_on')})",
             f"  новых: high={c.get('high', 0)} medium={c.get('medium', 0)} "
             f"low={c.get('low', 0)}",
             f"  всего сейчас: {res.get('current_count')} "
             f"(в базлайне: {res.get('baseline_count')}), "
             f"закрыто: {res.get('resolved')}"]
    for i in res.get("new", [])[:15]:
        lines.append(f"  + [{i['severity']}] {i['area']}: {i['detail']} "
                     f"({i['file']})")
    return "\n".join(lines)
