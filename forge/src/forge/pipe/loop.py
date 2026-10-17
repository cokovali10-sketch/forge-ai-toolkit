"""FORGE loop: замкнутый контур «проверь и почини».

Это то, что превращает конвейер (ОТК) в самопочиняющийся завод:

  checkpoint -> pipe -> SUCCESS? готово
                     -> FAILED?  собрать пакеты ремонта
                                 применить безопасные авто-фиксы
                                 вызвать внешний фиксер (--on-fail ХУК)
                                 повторить (до N попыток)

FORGE сам код не «додумывает»: он гарантирует страховку, откат, честный
статус и безопасные механические правки (повторяющиеся магические числа).
Умную правку делает мозг агента — через хук `on_fail`, который получает
целевую папку и пакеты ремонта.

Откат всегда одной командой: `forge fix rollback <dir>`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

OnFail = Callable[[str, list[dict[str, Any]]], dict[str, Any]]


def _bundles(report: dict[str, Any], forge_root: str) -> list[dict[str, Any]]:
    from forge.pipe.heal import _suggest
    out: list[dict[str, Any]] = []
    for s in report.get("stages", []):
        if s.get("status") == "SUCCESS" or s.get("cached"):
            continue
        err = s.get("error", {}) or {}
        text = str(err.get("message", "")) + " " + str(s.get("name", ""))
        files = sorted({f.get("file", "") for f in (err.get("sample", []) or [])
                        if f.get("file")})
        out.append({"stage": s.get("name"), "status": s.get("status"),
                    "error": err.get("message", ""), "files": files[:10],
                    "suggested_modules": _suggest(forge_root, text)})
    return out


def _candidate_files(bundles: list[dict[str, Any]], target: str,
                     limit: int = 50) -> list[str]:
    """Файлы для механических авто-фиксов: из пакетов, иначе — .py проекта."""
    files: list[str] = []
    for b in bundles:
        for f in b.get("files", []):
            if f and f not in files:
                files.append(f)
    if files:
        return files[:limit]
    base = Path(target)
    if base.is_dir():
        for p in sorted(base.rglob("*.py")):
            if any(part in (".git", ".venv", "venv", "__pycache__", "node_modules")
                   for part in p.parts):
                continue
            files.append(str(p))
            if len(files) >= limit:
                break
    return files


def run_loop(target: str, forge_root: str, max_attempts: int = 3,
             serial: bool = False, auto_fix: bool = True,
             on_fail: OnFail | None = None,
             stages=None) -> dict[str, Any]:
    """Гоняет конвейер и пытается довести проект до зелёного за N попыток."""
    from forge.fix import loop as _fix
    from forge.pipe.runner import PipeRunner
    from forge.pipe.stages import DEFAULT_STAGES

    stages = DEFAULT_STAGES if stages is None else stages
    safety = _fix.checkpoint(target, stash=False)  # неразрушающая: работу не прячем
    attempts: list[dict[str, Any]] = []
    fixed: list[str] = []

    for attempt in range(1, max_attempts + 1):
        runner = PipeRunner(
            stages, {"target": target, "forge_root": forge_root},
            checkpoint=str(Path(target) / "forge-pipe-checkpoint.json"))
        report = runner.run(serial=serial).to_dict()
        entry: dict[str, Any] = {"attempt": attempt, "status": report["status"]}
        if report["status"] == "SUCCESS":
            entry["result"] = "green"
            attempts.append(entry)
            return {"ok": True, "status": "SUCCESS", "attempts": attempts,
                    "safety_net": bool(safety.get("ok")), "fixed": fixed}
        attempts.append(entry)
        if attempt == max_attempts:
            break

        bundles = _bundles(report, forge_root)
        entry["bundles"] = bundles
        actions: list[dict[str, Any]] = []

        if auto_fix:
            from forge.refactor.apply import apply as _apply
            for f in _candidate_files(bundles, target):
                if Path(f).suffix.lower() != ".py":
                    continue
                r = _apply(f)
                if r.get("changed"):
                    actions.append({"fix": "magic-constants", "file": f,
                                    "constants": len(r.get("constants", {}))})
                    if f not in fixed:
                        fixed.append(f)

        if on_fail is not None:
            try:
                hook = on_fail(target, bundles)
            except Exception as e:  # noqa: BLE001 - чужой хук не должен ронять цикл
                hook = {"ok": False, "error": f"{type(e).__name__}: {e}"}
            actions.append({"hook": "on_fail", "ok": hook.get("ok"),
                            "detail": hook.get("detail") or hook.get("error", "")})

        entry["actions"] = actions
        if not actions:
            entry["stopped"] = "нечего чинить автоматически; нужен --on-fail"
            break

    return {"ok": False, "status": "FAILED", "attempts": attempts,
            "safety_net": bool(safety.get("ok")), "fixed": fixed,
            "hint": "смотри bundles; откат: forge fix rollback <dir>"}


def hook_command(cmd: list[str], target: str,
                 bundles_file: str = "forge-repair-bundles.json") -> OnFail:
    """Готовый хук: запускает внешнюю команду-фиксер в папке проекта."""
    import json

    def _run(tgt: str, bundles: list[dict[str, Any]]) -> dict[str, Any]:
        from forge.fix.loop import run_check
        try:
            Path(tgt, bundles_file).write_text(
                json.dumps(bundles, ensure_ascii=False, indent=2),
                encoding="utf-8")
        except OSError:
            pass
        res = run_check(cmd, tgt, timeout=900)
        return {"ok": res.get("ok"), "code": res.get("code"),
                "detail": (res.get("log", "") or "")[-500:]}

    return _run
