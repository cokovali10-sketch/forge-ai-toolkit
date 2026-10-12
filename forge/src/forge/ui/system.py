"""Design System format: JSON-validated tokens + built-in presets."""
from __future__ import annotations

import json
from pathlib import Path

REQUIRED_TOP = {"name", "version", "colors", "spacing", "radius",
                "typography", "components"}


def validate(system: dict) -> list[str]:
    errs = []
    for k in sorted(REQUIRED_TOP - set(system)):
        errs.append(f"missing section: {k}")
    colors = system.get("colors", {})
    if not isinstance(colors, dict) or not colors:
        errs.append("colors must be a non-empty map")
    else:
        import re
        for name, value in colors.items():
            if not isinstance(value, str) or not re.fullmatch(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})", value):
                errs.append(f"bad color {name}: {value!r} (want #RRGGBB[AA])")
    return errs


def preset_mythic() -> dict:
    """Dark-red glass system shared with MythicVisuals Theme.java."""
    return {
        "name": "mythic-dark-red",
        "version": "0.1.0",
        "colors": {
            "accent": "#B3121F",
            "accent_bright": "#E03040",
            "panel": "#100B0B",
            "panel_alpha": "#B8100B0B",
            "row": "#1A0E0E",
            "border": "#5A1218",
            "text": "#FFFFFFFF",
            "text_dim": "#B8A8A8",
        },
        "spacing": {"xs": 2, "s": 4, "m": 8, "l": 16, "xl": 24},
        "radius": {"s": 2, "m": 4, "l": 8},
        "typography": {"font": "minecraft:default", "title_size": 14,
                       "body_size": 9, "max_title_chars": 32},
        "components": {"button": {"h": 20, "pad": 6},
                       "row": {"h": 20}, "panel": {"border": 1}},
    }


def save(system: dict, path: str | Path) -> str:
    errs = validate(system)
    if errs:
        raise ValueError("; ".join(errs))
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(system, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(p)
