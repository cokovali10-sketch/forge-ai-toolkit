"""YAML через мост Anvil, с встроенным fallback для простых файлов.

Anvil yaml_* возвращают {"ok":..., "data"/"error"}. Нормализуем к виду
{"ok": bool, "value"/"error": ...} для единого API редактора.

Если Anvil рядом нет (или он ответил ошибкой), простые YAML-файлы —
вложенные словари, скаляры и списки скаляров — обрабатываются встроенным
построчным парсером. Он сохраняет порядок ключей, комментарии и отступы,
поэтому `forge edit` работает и на чистой машине без Anvil.
"""
from __future__ import annotations

import json
import math
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


# --- встроенный fallback -------------------------------------------------

def _split_comment(line: str) -> tuple[str, str]:
    """Отделяет хвостовой комментарий, не трогая `#` внутри кавычек."""
    quote = ""
    for i, ch in enumerate(line):
        if ch in "\"'":
            if not quote:
                quote = ch
            elif quote == ch:
                quote = ""
        elif ch == "#" and not quote and (i == 0 or line[i - 1] in " \t"):
            return line[:i], line[i:]
    return line, ""


def _unquote(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        if text[0] == '"':
            try:
                return str(json.loads(text))
            except ValueError:
                return text[1:-1]
        return text[1:-1].replace("''", "'")
    return text


def _scalar(text: str) -> Any:
    text = text.strip()
    if not text:
        return ""
    low = text.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "~"):
        return None
    if text[0] in "\"'":
        return _unquote(text)
    try:
        return json.loads(text)
    except ValueError:
        return text


def _compact(text: str) -> list[tuple[int, str]]:
    """Строки без пустых/комментариев: (отступ, содержимое)."""
    out: list[tuple[int, str]] = []
    for raw in text.splitlines():
        code, _ = _split_comment(raw)
        stripped = code.rstrip()
        if not stripped.strip() or stripped.strip() in ("---", "..."):
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        out.append((indent, stripped.strip()))
    return out


def _parse_map(items: list[tuple[int, str]], pos: int, indent: int):
    out: dict[str, Any] = {}
    while pos < len(items):
        cur, content = items[pos]
        if cur < indent or content.startswith("- "):
            break
        if cur > indent:
            pos += 1  # кривой отступ: не ломаем весь разбор
            continue
        key, sep, rest = content.partition(":")
        if not sep:
            pos += 1
            continue
        key, rest = _unquote(key), rest.strip()
        pos += 1
        if not key:
            continue
        if rest:
            # многострочный скаляр (|, >) — оставляем маркер как есть
            out[key] = _scalar(rest)
        elif pos < len(items) and items[pos][0] > cur:
            out[key], pos = _parse_block(items, pos, items[pos][0])
        else:
            out[key] = {}
    return out, pos


def _parse_list(items: list[tuple[int, str]], pos: int, indent: int):
    out: list[Any] = []
    while pos < len(items):
        cur, content = items[pos]
        if cur != indent or not content.startswith("- "):
            break
        item = content[2:].strip()
        pos += 1
        key, sep, rest = item.partition(":")
        if sep and key and not item.startswith(("\"", "'")) and " " not in key.strip():
            entry: dict[str, Any] = {}
            name, tail = _unquote(key), rest.strip()
            entry[name] = _scalar(tail) if tail else {}
            if pos < len(items) and items[pos][0] > cur:
                child, pos = _parse_block(items, pos, items[pos][0])
                if isinstance(child, dict):
                    entry.update(child)
            out.append(entry)
        else:
            out.append(_scalar(item))
    return out, pos


def _parse_block(items: list[tuple[int, str]], pos: int, indent: int):
    if pos < len(items) and items[pos][1].startswith("- "):
        return _parse_list(items, pos, indent)
    return _parse_map(items, pos, indent)


def _load_text(path: str) -> tuple[str, str]:
    try:
        return Path(path).read_text(encoding="utf-8"), ""
    except OSError as e:
        return "", f"{type(e).__name__}: {e}"


def _fallback_doc(path: str) -> tuple[Any, str]:
    text, err = _load_text(path)
    if err:
        return None, err
    doc, _ = _parse_block(_compact(text), 0, 0)
    return doc, ""


def _fallback_keys(path: str) -> dict[str, Any]:
    doc, err = _fallback_doc(path)
    if err:
        return {"ok": False, "error": err}
    return {"ok": True, "value": list(doc) if isinstance(doc, dict) else []}


def _fallback_get(path: str, dotted: str) -> dict[str, Any]:
    doc, err = _fallback_doc(path)
    if err:
        return {"ok": False, "error": err}
    cur: Any = doc
    for part in [p for p in dotted.split(".") if p]:
        if isinstance(cur, list) and part.lstrip("-").isdigit():
            idx = int(part)
            if not -len(cur) <= idx < len(cur):
                return {"ok": False, "error": f"нет такого индекса: {part}"}
            cur = cur[idx]
        elif isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return {"ok": False, "error": f"путь не найден: {dotted}"}
    return {"ok": True, "value": cur}


def _format_scalar(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return "null"
        return repr(value)
    text = str(value)
    unsafe = (not text or text != text.strip()
              or any(c in text for c in ":#{}[],&*!|>'\"%@`"))
    return json.dumps(text, ensure_ascii=False) if unsafe else text


def _line_index(text: str) -> dict[str, tuple[int, str]]:
    """dotted path -> (номер строки, исходная строка)."""
    index: dict[str, tuple[int, str]] = {}
    stack: list[tuple[int, str]] = []
    for i, raw in enumerate(text.splitlines()):
        code, _ = _split_comment(raw)
        body = code.rstrip()
        if not body.strip():
            continue
        indent = len(body) - len(body.lstrip(" "))
        content = body.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if content.startswith("- ") or ":" not in content:
            continue
        key = _unquote(content.partition(":")[0])
        if not key:
            continue
        index[".".join([k for _, k in stack] + [key])] = (i, raw)
        if not content.partition(":")[2].strip():
            stack.append((indent, key))
    return index


def _fallback_set(path: str, dotted: str, value: Any) -> dict[str, Any]:
    text, err = _load_text(path)
    if err:
        return {"ok": False, "error": err}
    index = _line_index(text)
    hit = index.get(dotted)
    if hit is None:
        return {"ok": False, "error": f"путь не найден: {dotted}"}
    lineno, raw = hit
    newline = "\r\n" if raw.endswith("\r") else ("\n" if raw.endswith("\n") else "")
    code, comment = _split_comment(raw.rstrip("\r\n"))
    trimmed = code.rstrip()
    gap = code[len(trimmed):]
    indent = trimmed[: len(trimmed) - len(trimmed.lstrip(" "))]
    key = trimmed.strip().partition(":")[0]
    line = f"{indent}{key}: {_format_scalar(value)}"
    if comment:
        line += gap + comment
    lines = text.splitlines(keepends=True)
    eol = "\r\n" if lines and lines[lineno].endswith("\r\n") else "\n"
    lines[lineno] = line + eol
    try:
        Path(path).write_text("".join(lines), encoding="utf-8")
    except OSError as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return {"ok": True, "value": {"path": path, "key": dotted, "value": value}}


def _normalize_keys(data: Any) -> Any:
    """Anvil кладёт список ключей в "sections", старые версии — в "keys"."""
    if isinstance(data, dict):
        for name in ("keys", "sections"):
            value = data.get(name)
            if isinstance(value, (list, tuple)):
                return list(value)
    return data


def _is_index_path(dotted: str) -> bool:
    return any(part.lstrip("-").isdigit() for part in dotted.split(".") if part)


# --- публичный API -------------------------------------------------------

def keys(path: str, anvil_dir: str = "") -> dict[str, Any]:
    d = anvil_dir or find_anvil()
    error = ""
    if d:
        r = _backend(d).call("yaml_keys", {"path": path})
        if r.get("ok"):
            return {"ok": True, "value": _normalize_keys(r.get("data", {}))}
        error = str(r.get("error", "?"))
    out = _fallback_keys(path)
    if out["ok"] or not error:
        return out
    return {"ok": False, "error": error}


def get(path: str, dotted: str, anvil_dir: str = "") -> dict[str, Any]:
    d = anvil_dir or find_anvil()
    error = ""
    if d and not _is_index_path(dotted):
        r = _backend(d).call("yaml_get_path", {"path": path, "key": dotted})
        if r.get("ok"):
            return {"ok": True, "value": r.get("data", {}).get("value")}
        error = str(r.get("error", "?"))
    out = _fallback_get(path, dotted)
    if out["ok"] or not error:
        return out
    return {"ok": False, "error": error}


def set(path: str, dotted: str, value: Any, anvil_dir: str = "") -> dict[str, Any]:
    d = anvil_dir or find_anvil()
    error = ""
    if d:
        r = _backend(d).call("yaml_set_path",
                             {"path": path, "key": dotted, "value": value})
        if r.get("ok"):
            data = r.get("data", {})
            return {"ok": True,
                    "value": data if isinstance(data, dict) else {"result": data}}
        error = str(r.get("error", "?"))
    out = _fallback_set(path, dotted, value)
    if out["ok"] or not error:
        return out
    return {"ok": False, "error": error}
