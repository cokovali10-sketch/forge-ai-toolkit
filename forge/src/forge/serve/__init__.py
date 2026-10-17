"""FORGE serve: единый локальный дашборд + JSON API по проекту."""
from .app import render_static, serve

__all__ = ["serve", "render_static"]
