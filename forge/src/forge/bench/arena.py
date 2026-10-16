"""FORGE Benchmark Arena: публичное табло «кто лучше решает задачи».

Честные правила (промпт §18):
- одна и та же задача, один и тот же кандидат-каталог, один замер = одна строка;
- таблица показывает ПОСЛЕДНИЙ прогон каждого агента (не лучший из 100);
- сырые строки хранятся в scoreboard.jsonl — любой может пересчитать.
Запись только явной командой (как майнер: никакой автоматики).
"""
from __future__ import annotations

import datetime as _dt
import json
import time
from pathlib import Path
from typing import Any


def record(tasks_dir: str | Path, candidate: str | Path, agent: str,
           board: str | Path) -> dict[str, Any]:
    """Прогнать suite и дописать строку в табло. Возвращает строку."""
    from forge.bench.runner import run_suite
    suite = run_suite(tasks_dir, candidate, agent)
    row = {"ts": int(time.time()), "agent": agent,
           "total": suite["total"], "passed": suite["passed"],
           "results": [{"task": r["task"], "passed": r["passed"]}
                       for r in suite["results"]]}
    bp = Path(board)
    try:
        if bp.parent and str(bp.parent) not in (".", ""):
            bp.parent.mkdir(parents=True, exist_ok=True)
        with open(bp, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as e:
        row["board_warning"] = f"не записал табло: {e}"
    row["suite"] = suite
    return row


def load_board(board: str | Path) -> list[dict[str, Any]]:
    p = Path(board)
    if not p.is_file():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def render(rows: list[dict[str, Any]]) -> str:
    """Markdown-таблица по последним прогонам каждого агента."""
    latest: dict[str, dict] = {}
    for r in rows:
        a = str(r.get("agent", "?"))
        if a not in latest or r.get("ts", 0) >= latest[a].get("ts", 0):
            latest[a] = r
    out = ["# FORGE Benchmark Arena", "",
           "Последний прогон каждого агента. Сырые данные: `scoreboard.jsonl`.", "",
           "| Агент | Задачи | Дата | Детали |",
           "|---|---|---|---|"]
    for agent in sorted(latest):
        r = latest[agent]
        det = ", ".join(f"{x['task']}:{'✓' if x['passed'] else '✗'}"
                        for x in r.get("results", []))
        ts = _dt.datetime.fromtimestamp(r.get("ts", 0)).strftime("%Y-%m-%d %H:%M")
        out.append(f"| {agent} | {r.get('passed')}/{r.get('total')} | {ts} | {det} |")
    if len(out) == 6:
        out.append("| — | — | — | прогонов пока нет |")
    return "\n".join(out) + "\n"
