"""FORGE edit API: одна логика для CLI, MCP и окна. Возвращает dict-результаты."""
from __future__ import annotations

import json as _json
import shutil
from pathlib import Path
from typing import Any

from forge.edit import objects as _o
from forge.edit import yaml_bridge as _y


def _is_yaml(path: str) -> bool:
    return Path(path).suffix.lower() in (".yml", ".yaml")


def _builtin_schema(name: str) -> Path | None:
    p = Path(__file__).resolve().parent / "schemas" / f"{name}.json"
    return p if p.is_file() else None


def _load_schema(ref: str) -> tuple[dict | None, str]:
    if not ref:
        return None, ""
    p = _builtin_schema(ref) or Path(ref)
    if not p.is_file():
        return None, f"нет схемы: {ref}"
    try:
        return _json.loads(p.read_text(encoding="utf-8")), ""
    except (OSError, ValueError) as e:
        return None, f"битая схема: {e}"


def inspect(file: str) -> dict[str, Any]:
    if _is_yaml(file):
        r = _y.keys(file)
        return {"file": file, "format": "yaml",
                "sections": r.get("value") if r.get("ok") else [],
                "error": r.get("error", "")}
    try:
        doc = _o._load(file)
    except (FileNotFoundError, ValueError) as e:
        return {"file": file, "format": "json", "error": str(e)}
    return {"file": file, "format": "json", "structure": _o.inspect_doc(doc)}


def get(file: str, dotted: str) -> dict[str, Any]:
    if _is_yaml(file):
        r = _y.get(file, dotted)
        return {"file": file, "path": dotted, **r}
    try:
        return {"file": file, "path": dotted, "ok": True,
                "value": _o.get(_o._load(file), dotted)}
    except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
        return {"file": file, "path": dotted, "ok": False,
                "error": f"{type(e).__name__}: {e}"}


def set(file: str, dotted: str, value_text: str, dry: bool = False,
        schema: str = "") -> dict[str, Any]:
    try:
        value = _json.loads(value_text)
    except ValueError:
        value = value_text  # не JSON — считаем строкой (показано в ответе)
        coerced = True
    else:
        coerced = False
    if _is_yaml(file):
        if dry:
            return {"file": file, "path": dotted, "ok": True, "dry": True,
                    "new": value if not coerced else value_text,
                    "coerced_to_string": coerced}
        try:
            shutil.copyfile(file, str(file) + ".forge-bak")
        except OSError as e:
            return {"file": file, "ok": False,
                    "error": f"бэкап не удался, не пишу: {e}"}
        r = _y.set(file, dotted, value if not coerced else value_text)
        out = {"file": file, "path": dotted, "dry": False, **r}
        if coerced:
            out["coerced_to_string"] = True
        return out
    try:
        doc = _o._load(file)
        new_doc, old = _o.set_value(doc, dotted, value)
    except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
        return {"file": file, "ok": False,
                "error": f"{type(e).__name__}: {e}"}
    if schema:
        sch, err = _load_schema(schema)
        if err:
            return {"file": file, "ok": False, "error": err}
        errs = _o.validate(new_doc, sch or {})
        if errs:
            return {"file": file, "ok": False,
                    "error": f"схема не прошла: {errs[:5]}"}
    if dry:
        return {"file": file, "path": dotted, "ok": True, "dry": True,
                "old": None if old is None else old, "new": value}
    try:
        bak = _o.write(file, new_doc, backup=True)
    except OSError as e:
        return {"file": file, "ok": False, "error": str(e)}
    return {"file": file, "path": dotted, "ok": True,
            "old": None if old is None else old, "new": value,
            "backup": bak, "coerced_to_string": coerced}


def validate(file: str, schema: str) -> dict[str, Any]:
    if not schema:
        return {"file": file, "ok": False,
                "error": "укажи схему: --schema NAME|PATH"}
    if _is_yaml(file):
        return {"file": file, "ok": False,
                "error": "YAML валидируется схемой только после конвертации; "
                         "пока: inspect/get/set"}
    sch, err = _load_schema(schema)
    if err:
        return {"file": file, "ok": False, "error": err}
    try:
        doc = _o._load(file)
    except (FileNotFoundError, ValueError) as e:
        return {"file": file, "ok": False, "error": str(e)}
    errs = _o.validate(doc, sch or {})
    return {"file": file, "ok": not errs, "errors": errs[:20]}


def rollback(file: str) -> dict[str, Any]:
    try:
        if _is_yaml(file):
            bak = Path(str(file) + ".forge-bak")
            if not bak.is_file():
                return {"file": file, "ok": False, "error": "нет бэкапа (.forge-bak)"}
            Path(file).write_bytes(bak.read_bytes())
            return {"file": file, "ok": True}
        _o.rollback(file)
        return {"file": file, "ok": True}
    except (FileNotFoundError, OSError) as e:
        return {"file": file, "ok": False, "error": str(e)}
