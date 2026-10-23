"""FORGE Factory: one intent -> built plugin -> live server -> report + zip."""
from __future__ import annotations

from .intent import plan, render_text
from .pipeline import run

__all__ = ["plan", "run", "render_text"]
