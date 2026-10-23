"""Web Studio presets: deterministic, dependency-free visual systems.

Every preset is a self-contained token set (colors, type, radius, effect)
plus the animation primitives the generator can switch on. No external
fonts, scripts or CDNs: the output works offline, straight from disk.
"""
from __future__ import annotations

PRESETS: dict[str, dict] = {
    "aurora": {
        "title": "Aurora",
        "hint": "тёмный космос, мягкие градиенты, частицы",
        "dark": True,
        "effect": "aurora",
        "radius": "20px",
        "display": "'Space Grotesk','Segoe UI',system-ui,sans-serif",
        "body": "Inter,'Segoe UI',system-ui,sans-serif",
        "colors": {
            "bg": "#060a17", "bg2": "#0c1330",
            "text": "#eaf1ff", "muted": "#a7b6d6",
            "accent": "#5eead4", "accent2": "#a78bfa",
            "surface": "rgba(255,255,255,.06)",
            "border": "rgba(255,255,255,.14)",
            "btn_text": "#041014",
            "glow": "rgba(94,234,212,.35)",
        },
        "animations": ["reveal", "tilt", "magnet", "particles",
                       "counter", "parallax"],
    },
    "neon": {
        "title": "Neon",
        "hint": "киберпанк, глитч, сетка и неон",
        "dark": True,
        "effect": "neon",
        "radius": "8px",
        "display": "'Space Grotesk','Segoe UI',system-ui,sans-serif",
        "body": "Inter,'Segoe UI',system-ui,sans-serif",
        "colors": {
            "bg": "#050509", "bg2": "#0b0516",
            "text": "#f5f3ff", "muted": "#b8a8d8",
            "accent": "#ff2ea6", "accent2": "#22d3ee",
            "surface": "rgba(255,46,166,.06)",
            "border": "rgba(255,46,166,.26)",
            "btn_text": "#120014",
            "glow": "rgba(255,46,166,.40)",
        },
        "animations": ["reveal", "tilt", "magnet", "particles",
                       "counter", "parallax", "glitch"],
    },
    "glass": {
        "title": "Glass",
        "hint": "стекло, размытие, глубокие блики",
        "dark": True,
        "effect": "glass",
        "radius": "22px",
        "display": "'Space Grotesk','Segoe UI',system-ui,sans-serif",
        "body": "Inter,'Segoe UI',system-ui,sans-serif",
        "colors": {
            "bg": "#0b1020", "bg2": "#1b2340",
            "text": "#f1f5f9", "muted": "#a8b6cf",
            "accent": "#7dd3fc", "accent2": "#c084fc",
            "surface": "rgba(255,255,255,.08)",
            "border": "rgba(255,255,255,.18)",
            "btn_text": "#06121c",
            "glow": "rgba(125,211,252,.35)",
        },
        "animations": ["reveal", "tilt", "magnet", "counter", "parallax"],
    },
    "brutalist": {
        "title": "Brutalist",
        "hint": "светлый бетон, толстые рамки, резкая тень",
        "dark": False,
        "effect": "brut",
        "radius": "0px",
        "display": "'JetBrains Mono','Consolas',monospace",
        "body": "'JetBrains Mono','Consolas',monospace",
        "colors": {
            "bg": "#f4f1e8", "bg2": "#fffdf5",
            "text": "#111111", "muted": "#4b4b4b",
            "accent": "#c2410c", "accent2": "#1d4ed8",
            "surface": "#ffffff",
            "border": "#111111",
            "btn_text": "#ffffff",
            "glow": "rgba(194,65,12,.18)",
        },
        "animations": ["reveal", "magnet", "counter", "marquee"],
    },
    "minimal": {
        "title": "Minimal",
        "hint": "светлый минимализм, тонкие линии, тишина",
        "dark": False,
        "effect": "minimal",
        "radius": "14px",
        "display": "'Space Grotesk','Segoe UI',system-ui,sans-serif",
        "body": "Inter,'Segoe UI',system-ui,sans-serif",
        "colors": {
            "bg": "#fafaf9", "bg2": "#ffffff",
            "text": "#141414", "muted": "#6b6b6b",
            "accent": "#2563eb", "accent2": "#0f766e",
            "surface": "#ffffff",
            "border": "#e5e5e5",
            "btn_text": "#ffffff",
            "glow": "rgba(37,99,235,.14)",
        },
        "animations": ["reveal", "magnet", "counter"],
    },
    "retro": {
        "title": "Retro CRT",
        "hint": "терминал, тёплый люминофор, сканлайны",
        "dark": True,
        "effect": "crt",
        "radius": "4px",
        "display": "'JetBrains Mono','Consolas',monospace",
        "body": "'JetBrains Mono','Consolas',monospace",
        "colors": {
            "bg": "#140f0a", "bg2": "#1f1710",
            "text": "#ffe8c7", "muted": "#c9a97c",
            "accent": "#ffb000", "accent2": "#33ff99",
            "surface": "rgba(255,176,0,.06)",
            "border": "rgba(255,176,0,.26)",
            "btn_text": "#1a1000",
            "glow": "rgba(255,176,0,.30)",
        },
        "animations": ["reveal", "magnet", "counter", "particles", "glitch"],
    },
}

DEFAULT_PRESET = "aurora"


def list_presets() -> list[dict]:
    """Human/agent friendly preset inventory."""
    return [{"key": key, "title": p["title"], "hint": p["hint"],
             "dark": p["dark"], "effect": p["effect"],
             "animations": list(p["animations"])}
            for key, p in PRESETS.items()]


def get(key: str) -> dict:
    """Preset by key; raises ValueError with the real choices."""
    k = (key or DEFAULT_PRESET).strip().lower()
    if k not in PRESETS:
        raise ValueError(f"unknown preset {key!r} (есть: {', '.join(PRESETS)})")
    return PRESETS[k]
