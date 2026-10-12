"""Module manifests (prompt section 5) + Expert Router.

A manifest is module.json: id, name, version, tech, capabilities, deps,
instructions, knowledge, tools, limits, permissions, tests, compat.
Router scores manifests against task text and explains its picks.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Manifest:
    id: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    tech: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    deps: list[str] = field(default_factory=list)
    instructions: str = ""
    knowledge: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    limits: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    compat: list[str] = field(default_factory=list)

    @staticmethod
    def load(path: str | Path) -> "Manifest":
        o = json.loads(Path(path).read_text(encoding="utf-8"))
        if not o.get("id"):
            raise ValueError(f"manifest without id: {path}")
        known = {f.name for f in Manifest.__dataclass_fields__.values()}
        return Manifest(**{k: v for k, v in o.items() if k in known})

    def validate(self) -> list[str]:
        errs = []
        if not self.id or " " in self.id:
            errs.append("bad id")
        for req in ("name", "version", "description", "instructions"):
            if not getattr(self, req):
                errs.append(f"missing {req}")
        if not self.capabilities:
            errs.append("no capabilities")
        if not self.permissions:
            errs.append("no permissions declared")
        return errs


def load_packs(packs_dir: str | Path) -> dict[str, Manifest]:
    out: dict[str, Manifest] = {}
    base = Path(packs_dir)
    if not base.is_dir():
        return out
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        f = child / "module.json"
        if f.is_file():
            try:
                m = Manifest.load(f)
                out[m.id] = m
            except (OSError, ValueError):
                continue
    return out


STOP = frozenset("""and with for the from that this into out via per use using used make made create add fix bug feature error issue problem project code file files test tests run build server client game mod mods api app web page panel menu button screen data base user users new old all any each every other same such than then there they their them those very via will would should could must shall may might can have has had does did are was were been being our your its it of to in on at as by or nor not but if then so yet""".split())


def route(task: str, packs: dict[str, Manifest], limit: int = 3) -> list[tuple[str, list[str]]]:
    """Score manifests by keyword overlap; return (id, reasons), best first."""
    words = {w.strip(".,!?()[]{}\"'").lower() for w in task.split()
             if len(w) > 2} - STOP
    scored: list[tuple[int, str, list[str]]] = []
    for m in packs.values():
        hay = " ".join(m.tech + m.capabilities + [m.description, m.instructions]).lower()
        hits = sorted({w for w in words if w in hay})
        if hits:
            scored.append((len(hits), m.id, [f"matches: {', '.join(hits[:6])}"]))
    scored.sort(key=lambda s: (-s[0], s[1]))
    return [(mid, reasons) for _, mid, reasons in scored[:limit]]
