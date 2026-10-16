"""FORGE edit objects: универсальный редактор документов.

JSON — свой движок (inspect/get/set/validate/rollback, ноль зависимостей).
YAML — через мост Anvil (yaml_get_path/yaml_set_path/yaml_keys), не дублируем.
Безопасность: лимит 4МБ, .bak перед записью, --dry без записи, validate
до set при --schema, rollback одной командой.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

MAX_DOC_BYTES = 4 * 1024 * 1024


def _load(path: str | Path) -> Any:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"нет файла: {p}")
    if p.stat().st_size > MAX_DOC_BYTES:
        raise ValueError(f"файл >4МБ ({p.stat().st_size}): не трогаем")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        raise ValueError(f"не JSON: {e}")


def _split(dotted: str) -> list[str | int]:
    parts: list[str | int] = []
    for seg in (dotted or "").split("."):
        if not seg:
            raise ValueError("пустой сегмент пути")
        parts.append(int(seg) if seg.lstrip("-").isdigit() else seg)
    if not parts:
        raise ValueError("пустой путь")
    return parts


def get(doc: Any, dotted: str) -> Any:
    cur = doc
    for seg in _split(dotted):
        if isinstance(seg, int):
            if not isinstance(cur, list) or not -len(cur) <= seg < len(cur):
                raise KeyError(f"нет индекса [{seg}]")
            cur = cur[seg]
        else:
            if not isinstance(cur, dict) or seg not in cur:
                raise KeyError(f"нет ключа '{seg}'")
            cur = cur[seg]
    return cur


def set_value(doc: Any, dotted: str, value: Any) -> Any:
    """Возвращает (new_doc, old_value|MISSING). Создаёт промежуточные dict."""
    parts = _split(dotted)
    doc = copy.deepcopy(doc)
    cur = doc
    for seg in parts[:-1]:
        if isinstance(seg, int):
            if not isinstance(cur, list):
                raise TypeError("индекс по не-списку")
            while len(cur) <= seg:
                cur.append({})
            cur = cur[seg]
        else:
            nxt = cur.get(seg) if isinstance(cur, dict) else None
            if not isinstance(nxt, (dict, list)):
                nxt = {}
                if isinstance(cur, dict):
                    cur[seg] = nxt
                else:
                    raise TypeError("путь через скаляр")
            cur = nxt
    last = parts[-1]
    if isinstance(last, int):
        if not isinstance(cur, list):
            raise TypeError("индекс по не-списку")
        while len(cur) <= last:
            cur.append(None)
        old = cur[last]
        cur[last] = value
    else:
        if not isinstance(cur, dict):
            raise TypeError("ключ по не-объекту")
        old = cur.get(last, _MISSING)
        cur[last] = value
    return doc, None if old is _MISSING else old


class _Missing:
    pass


_MISSING = _Missing()


def inspect_doc(doc: Any, _depth: int = 0, _max: int = 4) -> Any:
    """Структура: типы и ключи до глубины 4. Значения-скаляры — как есть (коротко)."""
    if isinstance(doc, dict):
        if _depth >= _max:
            return {"object": f"{len(doc)} keys…"}
        return {k: inspect_doc(v, _depth + 1, _max) for k, v in doc.items()}
    if isinstance(doc, list):
        if _depth >= _max:
            return [f"{len(doc)} items…"]
        return [inspect_doc(v, _depth + 1, _max) for v in doc[:5]] + (
            [f"…+{len(doc) - 5}"] if len(doc) > 5 else [])
    s = str(doc)
    return s if len(s) <= 60 else s[:60] + "…"


def validate(doc: Any, schema: dict) -> list[str]:
    """Лайт-валидатор: type/required/enum/min/max + вложенность. Пусто = ок."""
    errs: list[str] = []

    def _check(v: Any, s: dict, at: str) -> None:
        t = s.get("type")
        if t == "object":
            if not isinstance(v, dict):
                errs.append(f"{at or 'root'}: нужен object")
                return
            for k in s.get("required", []):
                if k not in v:
                    errs.append(f"{at or 'root'}: нет обязательного '{k}'")
            for k, sub in (s.get("properties", {}) or {}).items():
                if k in v:
                    _check(v[k], sub, f"{at}.{k}" if at else k)
        elif t == "array":
            if not isinstance(v, list):
                errs.append(f"{at or 'root'}: нужен array")
            elif "items" in s:
                for i, item in enumerate(v):
                    _check(item, s["items"], f"{at}[{i}]")
        elif t == "string":
            if not isinstance(v, str):
                errs.append(f"{at or 'root'}: нужен string")
            elif "enum" in s and v not in s["enum"]:
                errs.append(f"{at or 'root'}: '{v}' не из {s['enum']}")
        elif t == "integer":
            if not isinstance(v, int) or isinstance(v, bool):
                errs.append(f"{at or 'root'}: нужен integer")
            else:
                if "min" in s and v < s["min"]:
                    errs.append(f"{at or 'root'}: {v} < min {s['min']}")
                if "max" in s and v > s["max"]:
                    errs.append(f"{at or 'root'}: {v} > max {s['max']}")
        elif t == "number":
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                errs.append(f"{at or 'root'}: нужен number")
        elif t == "boolean":
            if not isinstance(v, bool):
                errs.append(f"{at or 'root'}: нужен boolean")

    _check(doc, schema, "")
    return errs


def write(path: str | Path, doc: Any, backup: bool = True) -> str:
    """Запись с .bak. Возвращает путь бэкапа или ''."""
    p = Path(path)
    bak = ""
    if backup and p.is_file():
        bak = str(p) + ".forge-bak"
        try:
            Path(bak).write_bytes(p.read_bytes())
        except OSError as e:
            raise OSError(f"бэкап не удался, не пишу: {e}")
    try:
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    except OSError as e:
        raise OSError(f"запись не удалась: {e}")
    return bak


def rollback(path: str | Path) -> None:
    bak = Path(str(path) + ".forge-bak")
    if not bak.is_file():
        raise FileNotFoundError("нет бэкапа (.forge-bak)")
    Path(path).write_bytes(bak.read_bytes())
