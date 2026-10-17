"""FORGE audit: одна команда — сводное здоровье проекта.

Композирует уже существующие честные проверки (без магии):
- карта проекта (языки, LOC, точки входа, внешние зависимости);
- утечки секретов (высокие важны сильнее всего);
- зависимости: гигиена версий;
- качество кода (советник refactor: оценка 0..100);
- с `deep=True` — ещё и родные тесты проекта.

Возвращает единый балл 0..100 как минимум по «худшей» области: одно серьёзное
открытие не должно тонуть в общей хорошей картине. Только чтение (кроме тестов,
которые запускает сам проект).
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

_PENALTY = {"high": 25, "medium": 2, "low": 1}


def audit(root: str | Path, deep: bool = False,
          max_files: int = 20000, timeout: float = 600.0) -> dict[str, Any]:
    """Сводный аудит проекта. Возвращает балл, вердикт и открытия."""
    base = Path(root)
    if not base.is_dir():
        return {"ok": False, "error": f"не директория: {base}"}

    from forge.kit.deps import scan_deps
    from forge.kit.project_map import build_map
    from forge.kit.secrets import scan_secrets
    from forge.refactor.api import inspect as _inspect

    findings: list[dict[str, Any]] = []
    sections: dict[str, Any] = {}

    m = build_map(base, max_files=max_files)
    sections["map"] = {
        "files": m.get("total_files", 0),
        "code_loc": m.get("code_loc", 0),
        "languages": [x["lang"] for x in m.get("languages", [])][:8],
        "external_deps": (m.get("imports") or {}).get("external_deps", [])[:12],
    }

    s = scan_secrets(base)
    if s.get("ok"):
        sections["secrets"] = {"count": s["count"],
                               "by_severity": s.get("by_severity", {})}
        for f in s["findings"]:
            findings.append({"severity": f["severity"], "area": "secrets",
                             "detail": f"{f['kind']} в {f['file']}"})
    else:
        sections["secrets"] = {"error": s.get("error")}

    d = scan_deps(base)
    if d.get("ok"):
        sections["deps"] = {"count": d["count"],
                            "by_ecosystem": d.get("by_ecosystem", {}),
                            "findings": len(d.get("findings", []))}
        for f in d.get("findings", []):
            findings.append({"severity": f["severity"], "area": "deps",
                             "detail": f"{f['kind']}: {f['detail']}"})
    else:
        sections["deps"] = {"error": d.get("error")}

    q = _inspect(base)
    qscore = int(q.get("score", 100)) if q.get("ok", True) else 100
    kinds: Counter = Counter()
    for ff in q.get("files_analyzed", []) or []:
        for i in ff.get("issues", []):
            kinds[i.get("kind", "?")] += 1
    qissues = int(q.get("total_issues", q.get("total", 0)) or 0)
    sections["quality"] = {"score": qscore, "issues": qissues,
                           "top_kinds": dict(kinds.most_common(8))}
    for kind, n in kinds.most_common(5):
        findings.append({"severity": "medium", "area": "quality",
                         "detail": f"{kind} x{n}"})

    if deep:
        from forge.kit.test_runner import run_tests
        t = run_tests(base, timeout=timeout)
        sections["tests"] = {"ran": t.get("ran"), "ok": t.get("ok"),
                             "kind": t.get("kind")}
        if t.get("ran") and not t.get("ok"):
            findings.append({"severity": "high", "area": "tests",
                             "detail": "родные тесты проекта падают"})

    penalty = sum(_PENALTY.get(f["severity"], 1) for f in findings)
    score = max(0, min(qscore, 100 - penalty))
    if score >= 85:
        verdict = "хорошо"
    elif score >= 60:
        verdict = "есть что чинить"
    else:
        verdict = "плохо"

    order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: order.get(f["severity"], 3))
    return {"ok": True, "root": str(base), "score": score, "verdict": verdict,
            "counts": {sev: sum(1 for f in findings if f["severity"] == sev)
                       for sev in ("high", "medium", "low")},
            "findings": findings[:30], "sections": sections}


def render_text(report: dict[str, Any]) -> str:
    if not report.get("ok"):
        return f"audit: {report.get('error')}"
    c = report.get("counts", {})
    lines = [f"FORGE audit: {report['root']}",
             f"  здоровье: {report['score']}/100 — {report['verdict']}",
             f"  открытий: high={c.get('high', 0)} "
             f"medium={c.get('medium', 0)} low={c.get('low', 0)}", ""]
    sec = report.get("sections", {})
    mp = sec.get("map", {})
    lines.append(f"Карта: {mp.get('files', 0)} файлов, "
                 f"{mp.get('code_loc', 0)} строк кода, "
                 f"языки: {', '.join(mp.get('languages', [])) or '—'}")
    sc = sec.get("secrets", {})
    lines.append(f"Секреты: {sc.get('count', 0)} "
                 f"({sc.get('by_severity', {})})")
    dp = sec.get("deps", {})
    lines.append(f"Зависимости: {dp.get('count', 0)} "
                 f"({dp.get('by_ecosystem', {})}), замечаний: "
                 f"{dp.get('findings', 0)}")
    ql = sec.get("quality", {})
    lines.append(f"Качество кода: {ql.get('score')}/100, замечаний: "
                 f"{ql.get('issues')}")
    if "tests" in sec:
        tt = sec["tests"]
        lines.append(f"Тесты: {'прогнаны' if tt.get('ran') else 'пропущены'} "
                     f"({tt.get('kind') or '—'}) — "
                     f"{'OK' if tt.get('ok') else 'FAIL'}")
    if report.get("findings"):
        lines += ["", "Главные открытия:"]
        for f in report["findings"][:12]:
            lines.append(f"  [{f['severity']}] {f['area']}: {f['detail']}")
    return "\n".join(lines)
