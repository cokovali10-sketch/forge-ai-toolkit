"""YAML через мост Anvil: не дублируем парсер, переиспользуем проверенный.

Anvil yaml_* возвращают {"ok":..., "data"/"error"}. Нормализуем к виду
{"ok": bool, "value"/"error": ...} для единого API редактора.
Без Anvil рядом — честная ошибка вместо тихого ничего.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def _backend(anvil_dir: str | Path):
    from forge.core.registry import AnvilBackend
    return AnvilBackend(anvil_dir)


def find_anvil() -> str:
    for cand in ("D:/PortfolioProjects/Anvil",
                 "D:/Forge-Factority/../PortfolioProjects/Anvil"):
        if (Path(cand) / "anvil_call.py").is_file():
            return cand
    here = Path(__file__).resolve()
    for up in [here.parent, *here.parents]:
        cand = up / "Anvil"
        if (cand / "anvil_call.py").is_file():
            return str(cand)
    return ""


def keys(path: str, anvil_dir: str = "") -> dict[str, Any]:
    d = anvil_dir or find_anvil()
    if not d:
        return {"ok": False, "error": "Anvil не найден рядом"}
    r = _backend(d).call("yaml_keys", {"path": path})
    if not r.get("ok"):
        return {"ok": False, "error": str(r.get("error", "?"))}
    data = r.get("data", {})
    return {"ok": True, "value": data.get("keys", data)}


def get(path: str, dotted: str, anvil_dir: str = "") -> dict[str, Any]:
    d = anvil_dir or find_anvil()
    if not d:
        return {"ok": False, "error": "Anvil не найден рядом"}
    r = _backend(d).call("yaml_get_path", {"path": path, "key": dotted})
    if not r.get("ok"):
        return {"ok": False, "error": str(r.get("error", "?"))}
    return {"ok": True, "value": r.get("data", {}).get("value")}


def set(path: str, dotted: str, value: Any, anvil_dir: str = "") -> dict[str, Any]:
    d = anvil_dir or find_anvil()
    if not d:
        return {"ok": False, "error": "Anvil не найден рядом"}
    r = _backend(d).call("yaml_set_path",
                         {"path": path, "key": dotted, "value": value})
    if not r.get("ok"):
        return {"ok": False, "error": str(r.get("error", "?"))}
    data = r.get("data", {})
    return {"ok": True, "value": data if isinstance(data, dict) else {"result": data}}
