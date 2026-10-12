"""Rendering strategies A/B/C/D with honest capability docs."""
from __future__ import annotations

STRATEGIES = {
    "A": {
        "name": "Inventory GUI",
        "for": "standard Paper/Bukkit plugins",
        "can": ["54-slot menus", "click handlers", "pagination", "Adventure text",
                "custom items", "CustomModelData", "configs", "permissions"],
        "cannot": ["free pixels", "fullscreen", "animations beyond scheduler ticks",
                   "custom fonts without resource pack"],
        "deps": ["paper-api"],
        "fallback": "works fully without resource pack or client mod",
    },
    "B": {
        "name": "Resource-Pack Composed UI",
        "for": "rich compositions inside inventory limits",
        "can": ["custom fonts/glyphs", "layered textures", "precise offsets",
                "themed frames"],
        "cannot": ["free positioning", "true animation", "anything outside 54 slots"],
        "deps": ["paper-api", "resource pack installed by player"],
        "fallback": "degrades to strategy A without the pack",
    },
    "C": {
        "name": "Client-Side UI",
        "for": "full custom screens (needs a client mod)",
        "can": ["free layout", "animations", "custom graphics", "complex states"],
        "cannot": ["vanilla clients", "server-only distribution"],
        "deps": ["compatible client mod (e.g. MythicVisuals-class)"],
        "fallback": "unavailable on vanilla; needs strategy A fallback screen",
    },
    "D": {
        "name": "Hybrid UI",
        "for": "server plugin + pack + client component combined",
        "can": ["everything above where each layer fits"],
        "cannot": ["single-artifact distribution"],
        "deps": ["paper-api", "resource pack", "client mod"],
        "fallback": "per-layer degradation (B->A, C->A)",
    },
}


def select(needs_client_mod: bool, needs_resource_pack: bool) -> dict:
    """Strategy choice from brief flags. Deterministic, documented."""
    if needs_client_mod:
        key = "D" if needs_resource_pack else "C"
    elif needs_resource_pack:
        key = "B"
    else:
        key = "A"
    out = {"key": key}
    out.update(STRATEGIES[key])
    return out
