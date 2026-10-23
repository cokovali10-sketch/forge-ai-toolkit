"""Web landing generator (backwards-compatible entry point).

Delegates to FORGE Web Studio: presets, real motion, contrast audit.
`forge gen web` and MCP `gen.web` keep working; `forge web` adds the
full studio surface (presets / new / audit / preview).
"""
from __future__ import annotations

from pathlib import Path


def generate(out_dir: str | Path, name: str = "Site",
             preset: str = "aurora", tagline: str = "",
             lang: str = "ru") -> dict:
    """Generates a static site. Returns {dir, files, ok, problems}."""
    from forge.webstudio import generate as _generate
    res = _generate(out_dir, name, preset=preset, tagline=tagline, lang=lang)
    return {
        "dir": res["dir"],
        "files": res["files"],
        "ok": res["ok"],
        "problems": res["problems"],
        "preset": res["preset"],
        "score": res["score"],
        "audit": res["audit"],
    }
