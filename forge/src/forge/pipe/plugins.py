"""FORGE pipe plugins: project-local stages without touching the core.

Convention: `<target>/.forge-stages/*.py`, each file exposes either
`STAGE: Stage` or `stages() -> list[Stage]`. Loaded with importlib,
no install needed. A broken plugin is SKIPPED with a warning — it never
fails someone else's pipeline. No network, no sandbox escape beyond
what the user already runs locally: plugins are code, review them.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


def load_plugins(target: str | Path) -> tuple[list, dict[str, str]]:
    """Returns (stages, skipped{file: error})."""
    from forge.pipe.stages import Stage
    d = Path(target) / ".forge-stages"
    stages: list[Stage] = []
    skipped: dict[str, str] = {}
    if not d.is_dir():
        return stages, skipped
    for f in sorted(d.glob("*.py")):
        if f.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(
                f"forge_stage_plugin_{f.stem}", f)
            if spec is None or spec.loader is None:
                raise ImportError("no loader")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except Exception as e:  # noqa: BLE001 - broken plugin, not broken pipe
            skipped[f.name] = f"{type(e).__name__}: {e}"[:200]
            continue
        found: list = []
        if isinstance(getattr(mod, "STAGE", None), Stage):
            found = [mod.STAGE]
        elif callable(getattr(mod, "stages", None)):
            try:
                found = list(mod.stages() or [])
            except Exception as e:  # noqa: BLE001
                skipped[f.name] = f"stages(): {type(e).__name__}: {e}"[:200]
                continue
        else:
            skipped[f.name] = "no STAGE or stages() found"
            continue
        bad = [s for s in found if not isinstance(s, Stage)]
        if bad:
            skipped[f.name] = f"{len(bad)} objects are not Stage"
            continue
        stages.extend(found)
    return stages, skipped
