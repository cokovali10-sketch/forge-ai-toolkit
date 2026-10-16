"""FORGE pipe heal: самолечение как процесс, а не магия.

 heal = checkpoint -> run -> SUCCESS? отчёт : пакеты ремонта + страховка.

Автоправку кода делает агент-мозг (его здесь нет и не должно быть:
промпт запрещает выдавать чужую работу за свою). Конвейер делает всё
остальное: страховку до прогона, структурные пакеты для чинящего
(стадия, ошибка, файлы, подсказанные модули-эксперты) и откат одной
командой (`forge fix rollback <dir>`).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _suggest(forge_root: str, text: str) -> list[dict[str, Any]]:
    try:
        from forge.modules.manifest import load_packs, route
        packs = load_packs(Path(forge_root) / "module-packs")
        return [{"module": mid, "why": reasons}
                for mid, reasons in route(text, packs)][:3]
    except Exception:
        return []


def heal(target: str, forge_root: str,
         stages=None, serial: bool = False) -> dict[str, Any]:
    from forge.fix import loop as _fix
    from forge.pipe.runner import PipeRunner
    from forge.pipe.stages import DEFAULT_STAGES
    stages = DEFAULT_STAGES if stages is None else stages
    out: dict[str, Any] = {"target": target, "healed": False,
                           "needed": False, "safety_net": False}
    cp = _fix.checkpoint(target)
    out["safety_net"] = bool(cp.get("ok"))
    if not cp.get("ok"):
        out["safety_warning"] = f"без страховки: {cp.get('error', '?')}"
    runner = PipeRunner(stages, {"target": target, "forge_root": forge_root},
                        checkpoint=str(Path(target) / "forge-pipe-checkpoint.json"))
    report = runner.run(serial=serial)
    out["report"] = report.to_dict()
    if report.status == "SUCCESS":
        return out
    out["needed"] = True
    bundles = []
    for s in report.to_dict()["stages"]:
        if s.get("status") == "SUCCESS" or s.get("cached"):
            continue
        err = s.get("error", {}) or {}
        text = err.get("message", "") + " " + s.get("name", "")
        files = sorted({f.get("file", "") for f in
                        (err.get("sample", []) or []) if f.get("file")})
        bundles.append({"stage": s.get("name"), "status": s.get("status"),
                        "error": err.get("message", ""),
                        "files": files[:10],
                        "suggested_modules": _suggest(forge_root, text)})
    out["bundles"] = bundles
    bp = Path(target) / "forge-repair-bundles.json"
    try:
        bp.write_text(json.dumps(bundles, ensure_ascii=False, indent=2),
                      encoding="utf-8")
        out["bundles_file"] = str(bp)
    except OSError:
        pass
    return out
