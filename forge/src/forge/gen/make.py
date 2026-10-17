"""FORGE make: штамповка проектов. Скаффолд + проверка одним вызовом.

gen/<kind>.generate() строит, конвейер тут же проверяет свежее.
Используют: CLI `forge make`, MCP `make.project`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def make(kind: str, name: str, out: str | Path, forge_root: str | Path) -> dict[str, Any]:
    from forge.gen import go_cli as _g
    from forge.gen import python_service as _p
    from forge.gen import web as _w
    mods = {"web": _w, "python-service": _p, "go-cli": _g}
    if kind not in mods:
        return {"ok": False, "error": f"unknown kind (есть: {','.join(mods)})"}
    dest = Path(out) / name if Path(out).name != name else Path(out)
    try:
        gen_res = mods[kind].generate(dest, name)
    except (ValueError, OSError) as e:
        return {"ok": False, "error": f"скаффолд не удался: {e}"}
    if not gen_res.get("ok"):
        return {"ok": False, "error": "скаффолд невалиден",
                "gen": gen_res}
    from forge.pipe.runner import PipeRunner
    from forge.pipe.stages import DEFAULT_STAGES
    rep = PipeRunner(list(DEFAULT_STAGES),
                     {"target": str(dest), "forge_root": str(forge_root)},
                     checkpoint=str(dest / "forge-pipe-checkpoint.json")).run()
    ok = rep.status == "SUCCESS"
    return {"ok": ok, "dir": str(dest), "gen": gen_res,
            "pipe": rep.status,
            "stages": [(s["name"], s.get("status")) for s in rep.to_dict()["stages"]]}
