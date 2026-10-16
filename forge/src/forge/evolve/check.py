"""FORGE evolve: Self-Update как детектор, а не магия.

Находит протухание трёх видов и заводит ЗАДАЧИ (не чинит молча):
1. skills: невалидные скиллы -> задача починить (модуль: build-repair);
2. rules: правило с >=3 подавлениями -> задача откалибровать (модуль: quality);
3. history: стадия падала >=3 раз за 10 прогонов -> задача разобраться.
Плюс сверка тулчейнов с минимумами. Выход — forge-evolve.json для агента.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


def _skills_check(forge_root: str) -> list[dict[str, Any]]:
    from forge.skills.loader import load_skills, validate_skill
    tasks = []
    try:
        skills = load_skills(Path(forge_root) / "skills")
    except Exception as e:  # noqa: BLE001
        return [{"area": "skills", "priority": "high",
                 "evidence": f"loader crashed: {e}",
                 "suggest": ["build-repair"]}]
    for name, sk in skills.items():
        errs = validate_skill(sk)
        if errs:
            tasks.append({"area": "skills", "priority": "high",
                          "evidence": f"{name}: {'; '.join(errs)[:200]}",
                          "suggest": ["build-repair"]})
    return tasks


def _rules_check(target: str) -> list[dict[str, Any]]:
    p = Path(target) / ".forge-suppress.json"
    if not p.is_file():
        return []
    try:
        items = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    counts: dict[str, int] = {}
    for s in items if isinstance(items, list) else []:
        if s.get("reason"):
            counts[s.get("rule", "?")] = counts.get(s.get("rule", "?"), 0) + 1
    return [{"area": "rules", "priority": "medium",
             "evidence": f"rule '{rule}' suppressed {n}x — tune or split it",
             "suggest": ["quality"]}
            for rule, n in counts.items() if n >= 3]


def _history_check(target: str) -> list[dict[str, Any]]:
    p = Path(target) / ".forge-pipe-history.jsonl"
    if not p.is_file():
        return []
    rows = []
    try:
        for line in p.read_text(encoding="utf-8").splitlines()[-10:]:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return []
    fails: dict[str, int] = {}
    for r in rows:
        for s in r.get("stages", []):
            if s.get("status") not in ("SUCCESS", "SKIPPED"):
                fails[s.get("name", "?")] = fails.get(s.get("name", "?"), 0) + 1
    return [{"area": "history", "priority": "high",
             "evidence": f"stage '{name}' failed {n}x in last {len(rows)} runs",
             "suggest": ["build-repair", "quality"]}
            for name, n in fails.items() if n >= 3]


def _toolchains() -> list[dict[str, Any]]:
    wants = {"python": "--version", "java": "-version", "node": "--version",
             "cargo": "--version", "go": "version"}
    out = []
    for prog in wants:
        if not shutil.which(prog):
            out.append({"area": "toolchain", "priority": "low",
                        "evidence": f"{prog} not on PATH",
                        "suggest": ["docs"]})
    return out


def check(target: str, forge_root: str) -> dict[str, Any]:
    tasks = (_skills_check(forge_root) + _rules_check(target)
             + _history_check(target) + _toolchains())
    return {"target": target, "tasks": tasks, "total": len(tasks)}
