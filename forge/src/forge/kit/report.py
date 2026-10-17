"""FORGE report: единый сводный отчёт по проекту для людей и агентов.

Композирует уже существующие честные проверки в один JSON:
- audit (карта/секреты/зависимости/качество + балл и вердикт);
- история качества и тренд (`quality-history`);
- история прогонов конвейера (`.forge-pipe-history.jsonl`);
- доска арены (`benchmarks/scoreboard.jsonl`), если есть;
- окружение (`doctor`): какие инструменты доступны.

Только чтение. Никаких записей и никаких запусков тестов (кроме `deep=True`).
Один и тот же словарь отдаёт и MCP-инструмент, и веб-дашборд `forge serve`.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from forge.kit.audit import audit

_DEFAULT_FORGE_ROOT = str(Path(__file__).resolve().parents[3])


def _read_jsonl(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    except OSError:
        return []
    return rows


def _pipe_history(base: Path, limit: int) -> list[dict[str, Any]]:
    return _read_jsonl(base / ".forge-pipe-history.jsonl", limit)


def _arena(base: Path, limit: int) -> list[dict[str, Any]]:
    for cand in (base / "benchmarks" / "scoreboard.jsonl",
                 base / ".forge-arena.jsonl"):
        rows = _read_jsonl(cand, limit)
        if rows:
            return rows
    return []


def _quality(base: Path, forge_root: str, limit: int) -> dict[str, Any]:
    try:
        from forge.quality import dashboard as _dash
        hist = _dash.history(str(base), forge_root, limit=limit)
        return {"history": hist, "trend": _dash.trend(str(base), forge_root)}
    except Exception:
        return {"history": [],
                "trend": {"direction": "flat", "delta": 0, "samples": 0}}


def _doctor(base: Path) -> dict[str, Any]:
    try:
        from forge.kit.doctor import doctor
        d = doctor(str(base))
        tools = d.get("tools", []) if isinstance(d, dict) else []
        return {"available": sum(1 for t in tools if t.get("present")),
                "total": len(tools),
                "capabilities": d.get("capabilities", {}),
                "tools": [{"name": t.get("name"), "present": t.get("present"),
                           "version": t.get("version")} for t in tools]}
    except Exception:
        return {"available": 0, "total": 0, "capabilities": {}, "tools": []}


def full_report(root: str | Path, deep: bool = False,
                forge_root: str | None = None, limit: int = 30,
                with_doctor: bool = True) -> dict[str, Any]:
    """Единый сводный отчёт. Возвращает тот же словарь, что видит дашборд."""
    base = Path(root)
    rep = audit(base, deep=deep)
    if not rep.get("ok"):
        return rep
    fr = forge_root or _DEFAULT_FORGE_ROOT
    out: dict[str, Any] = dict(rep)
    out["audit"] = {"score": rep["score"], "verdict": rep["verdict"],
                    "counts": rep.get("counts", {})}
    out["quality"] = _quality(base, fr, limit)
    out["pipe"] = _pipe_history(base, limit)
    out["arena"] = _arena(base, limit)
    out["doctor"] = _doctor(base) if with_doctor else {"available": 0,
                                                       "total": 0, "tools": []}
    out["generated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return out


def render_text(rep: dict[str, Any]) -> str:
    """Человекочитаемый свод: audit + тренд + конвейер + арена + окружение."""
    from forge.kit.audit import render_text as _audit_text
    lines = [_audit_text(rep)]
    q = rep.get("quality", {})
    tr = q.get("trend", {})
    lines.append(f"Тренд качества: {tr.get('direction', 'flat')} "
                 f"({tr.get('delta', 0):+g}), замеров: {tr.get('samples', 0)}")
    pipe = rep.get("pipe", [])
    if pipe:
        last = pipe[-1]
        lines.append(f"Конвейер: последний прогон {last.get('status', '?')} "
                     f"({last.get('duration_ms', 0)}мс), всего: {len(pipe)}")
    aren = rep.get("arena", [])
    if aren:
        passed = sum(1 for r in aren if r.get("passed") or r.get("ok"))
        lines.append(f"Арена: {passed}/{len(aren)} задач пройдено")
    doc = rep.get("doctor", {})
    lines.append(f"Окружение: {doc.get('available', 0)}/{doc.get('total', 0)} "
                 f"инструментов доступно")
    return "\n".join(lines)
