"""Intent -> plugin spec. Deterministic keyword routing, no model calls.

Example: "сделай плагин магазин с GUI и анимациями" becomes a real spec
(name, package, command, features, theme preset) the pipeline can build.
"""
from __future__ import annotations

import re

DOMAINS = [
    ("shop", ["shop", "магазин", "store", "покупк", "buy"], "ForgeShop", "shop"),
    ("auction", ["auction", "аукцион", "bid", "ставк"], "ForgeAuction", "auction"),
    ("kits", ["kit", "кит", "набор", "loadout"], "ForgeKits", "kit"),
    ("clans", ["clan", "клан", "guild", "гильд"], "ForgeClans", "clan"),
    ("teleport", ["tpa", "teleport", "телепорт", "телепорт"], "ForgeTPA", "tpa"),
    ("stats", ["stats", "статистик", "leaderboard", "топ"], "ForgeStats", "stats"),
    ("chat", ["chat", "чат"], "ForgeChat", "chat"),
    ("backup", ["backup", "бэкап", "резервн"], "ForgeBackup", "backup"),
]

FEATURES = [
    ("gui", ["gui", "гуи", "интерфейс", "меню", "menu", "inventory"]),
    ("animation", ["animation", "анимац", "animated"]),
    ("resourcepack", ["resourcepack", "resource pack", "текстур", "texture"]),
    ("economy", ["economy", "экономик", "vault", "деньг", "coins"]),
    ("storage", ["database", "база данных", "sqlite", "storage", "persist"]),
    ("permissions", ["permission", "права", "permission"]),
    ("api", ["api", "интеграц", "integration"]),
    ("tests", ["test", "тест"]),
]

STYLE_PRESETS = [
    ("cyberpunk", "neon"), ("sci-fi", "neon"), ("neon", "neon"),
    ("dark fantasy", "aurora"), ("fantasy", "aurora"),
    ("medieval", "retro"), ("industrial", "brutalist"),
    ("minimal", "minimal"), ("luxury", "glass"),
]


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "", name or "")
    if not slug or not slug[0].isalpha():
        raise ValueError(f"bad plugin name: {name!r}")
    return slug[0].upper() + slug[1:]


def _valid_package(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+", value))


def _valid_command(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z][a-z0-9_]*", value))


def _domain(text: str) -> tuple[str, str, str]:
    low = text.lower()
    for key, words, default_name, command in DOMAINS:
        if any(word in low for word in words):
            return key, default_name, command
    return "generic", "ForgePlugin", "hello"


def _features(text: str) -> list[str]:
    low = text.lower()
    out = ["config"]
    for key, words in FEATURES:
        if any(word in low for word in words):
            out.append(key)
    return out


def _style(text: str) -> tuple[str, str]:
    low = text.lower()
    try:
        from forge.ui.brief import from_description
        br = from_description(text)
        style = br.style
    except Exception:
        style = "minimal premium"
    preset = "aurora"
    for needle, choice in STYLE_PRESETS:
        if needle in low or needle in style:
            preset = choice
            break
    return style, preset


def plan(intent: str, name: str = "", package: str = "", command: str = "",
         api: str = "1.21", version: str = "0.1.0") -> dict:
    """Parse intent into a buildable spec. Raises ValueError on bad ids."""
    text = " ".join((intent or "").split())
    if not text:
        raise ValueError("empty intent")
    domain, default_name, default_command = _domain(text)
    plugin_name = _slug(name or default_name)
    package = package or f"com.forge.{domain}"
    if not _valid_package(package):
        raise ValueError(f"bad package: {package!r} (want a.b.c)")
    cmd = (command or default_command).lower()
    if not _valid_command(cmd):
        raise ValueError(f"bad command: {command!r} (want [a-z][a-z0-9_]*)")
    features = _features(text)
    style, preset = _style(text)
    screens: list[str] = []
    try:
        from forge.ui.brief import from_description
        screens = from_description(text).screens
    except Exception:
        pass
    description = text[:120]
    return {
        "intent": text,
        "domain": domain,
        "name": plugin_name,
        "class": _slug(plugin_name),
        "package": package,
        "command": cmd,
        "description": description,
        "api": api,
        "version": version,
        "features": features,
        "style": style,
        "preset": preset,
        "screens": screens,
        "resourcepack": "resourcepack" in features,
        "gui": "gui" in features,
        "stages": ["generate", "validate"] +
                  (["resourcepack"] if "resourcepack" in features else []) +
                  ["build", "e2e", "package"],
    }


def render_text(spec: dict) -> str:
    return (f"factory plan: {spec['name']} ({spec['package']}.{spec['class']})\n"
            f"  domain: {spec['domain']} · command: /{spec['command']}\n"
            f"  features: {', '.join(spec['features'])}\n"
            f"  style: {spec['style']} · preset: {spec['preset']}\n"
            f"  stages: {' -> '.join(spec['stages'])}")
