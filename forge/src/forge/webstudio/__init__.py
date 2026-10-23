"""FORGE Web Studio: animated, dependency-free landing generator + audit."""
from __future__ import annotations

from .site_audit import audit, contrast, render_text
from .generator import KNOWN_ANIMATIONS, generate
from .presets import DEFAULT_PRESET, PRESETS, get, list_presets
from .preview import serve_site

__all__ = ["generate", "audit", "render_text", "contrast", "list_presets",
           "get", "PRESETS", "DEFAULT_PRESET", "KNOWN_ANIMATIONS",
           "serve_site"]
