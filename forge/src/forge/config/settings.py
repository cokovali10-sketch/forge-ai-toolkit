"""FORGE configuration: forge.toml with validation.

Search order: --config flag > ./forge.toml > ~/.config/forge/config.toml.
Only known keys accepted; unknown keys are reported, not silently kept.
"""
from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover (py3.10 fallback)
    import tomli as tomllib  # type: ignore[no-redef]

DEFAULTS = {
    "workspace": ".",
    "anvil_dir": "D:/PortfolioProjects/Anvil",
    "hermes_url": "http://127.0.0.1:8765",
    "ollama_host": "http://localhost:11434",
    "lab_java21": r"C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot\bin\java.exe",
    "lab_servers": "D:/Forge-Factority/lab-servers",
    "fix_max_attempts": 5,
    "fix_timeout": 900,
    "default_model": "",
}

TYPES = {"workspace": str, "anvil_dir": str, "hermes_url": str,
         "ollama_host": str, "lab_java21": str, "lab_servers": str,
         "fix_max_attempts": int, "fix_timeout": int, "default_model": str}


def find_config(explicit: str = "") -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    local = Path("forge.toml")
    if local.is_file():
        return local
    home = Path.home() / ".config" / "forge" / "config.toml"
    if home.is_file():
        return home
    return None


def load(path: str | Path | None = None) -> tuple[dict, list[str]]:
    """Returns (config, warnings). Unknown keys + type errors -> warnings."""
    cfg = dict(DEFAULTS)
    warnings: list[str] = []
    p = Path(path) if path else find_config()
    if p is None:
        warnings.append("no forge.toml found, using defaults")
        return cfg, warnings
    try:
        raw = tomllib.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return cfg, [f"unreadable {p}: {type(e).__name__}: {e}; using defaults"]
    flat = raw.get("forge", raw) if isinstance(raw, dict) else {}
    if not isinstance(flat, dict):
        return cfg, [f"bad root in {p}; using defaults"]
    for k, v in flat.items():
        if k not in DEFAULTS:
            warnings.append(f"unknown key ignored: {k}")
            continue
        want = TYPES[k]
        if want is int:
            try:
                cfg[k] = int(v)
                continue
            except (TypeError, ValueError):
                warnings.append(f"bad int for {k}: {v!r}; using default")
                continue
        if not isinstance(v, str):
            warnings.append(f"bad string for {k}; using default")
            continue
        cfg[k] = v
    return cfg, warnings


def example() -> str:
    lines = ["[forge]"]
    for k, v in DEFAULTS.items():
        lines.append(f"# {k} = {v!r}" if isinstance(v, str) else f"# {k} = {v}")
    return "\n".join(lines) + "\n"
