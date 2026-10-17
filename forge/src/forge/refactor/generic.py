"""FORGE refactor: эвристический анализатор для языков без Python-AST.

JS/TS, Go, C++, Java, Kotlin, Rust — читаем по скобкам и отступам:
- магические числа (после вырезания комментариев и строк)
- дублирующиеся блоки (3+ одинаковые строки)
- длинные функции (>50 строк) — по совпадающим фигурным скобкам
- слишком много аргументов (>4)
- глубокая вложенность (>3 уровней внутри функции)

Это эвристика: результаты честно помечаются как приблизительные, но каждая
находка привязана к реальной строке файла — ничего не выдумывается.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from forge.refactor.clean_code import Issue, _duplicate_blocks, score_of

_NUM = re.compile(r"(?<![\w.])(\d{2,}(?:\.\d+)?)(?![\w.])")
_TRIVIAL = {0.0, 1.0, 2.0, 10.0, 100.0, -1.0}


def _strip_code(text: str) -> str:
    """Убирает // и /* */ комментарии и строковые литералы, сохраняя переводы
    строк — чтобы номера строк и длина не сдвигались."""
    out: list[str] = []
    i, n = 0, len(text)
    quote = ""
    line_comment = False
    block_comment = False
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if line_comment:
            if c == "\n":
                line_comment = False
                out.append(c)
            else:
                out.append(" ")
        elif block_comment:
            if c == "*" and nxt == "/":
                block_comment = False
                out.append("  ")
                i += 1
            else:
                out.append("\n" if c == "\n" else " ")
        elif quote:
            if c == "\\":
                out.append("  ")
                i += 1
            elif c == quote:
                quote = ""
                out.append(" ")
            else:
                out.append("\n" if c == "\n" else " ")
        elif c == "/" and nxt == "/":
            line_comment = True
            out.append("  ")
            i += 1
        elif c == "/" and nxt == "*":
            block_comment = True
            out.append("  ")
            i += 1
        elif c in "\"'`":
            quote = c
            out.append(" ")
        else:
            out.append(c)
        i += 1
    return "".join(out)


def _count_args(sig: str) -> int:
    """Число аргументов в списке параметров (по запятым верхнего уровня)."""
    s = sig.strip()
    if not s or s in ("void", "()"):
        return 0
    depth = 0
    commas = 0
    for ch in s:
        if ch in "([{<":
            depth += 1
        elif ch in ")]}>":
            depth -= 1
        elif ch == "," and depth == 0:
            commas += 1
    return commas + 1


def _match_braces(text: str, start: int, line_starts: list[int]) -> tuple[int, int]:
    """Возвращает (последняя_строка, макс_внутренняя_глубина) для блока с '{'."""
    depth = 0
    max_depth = 0
    i, n = start, len(text)
    end_line = line_starts[min(0, len(line_starts) - 1)]
    while i < n:
        c = text[i]
        if c == "{":
            depth += 1
            max_depth = max(max_depth, depth)
        elif c == "}":
            depth -= 1
            if depth == 0:
                end_line = i  # абсолютный индекс
                break
        i += 1
    return end_line, max(0, max_depth - 1)


def _line_of(pos: int, line_starts: list[int]) -> int:
    import bisect
    return bisect.bisect_right(line_starts, pos)


def _scan_functions(stripped: str, raw_lines: list[str],
                    fname: str) -> list[Issue]:
    issues: list[Issue] = []
    lines = stripped.splitlines()
    line_starts: list[int] = [0]
    for ln in lines:
        line_starts.append(line_starts[-1] + len(ln) + 1)
    for idx, line in enumerate(lines):
        s = line.rstrip()
        if "{" not in s or ")" not in s:
            continue
        lp = s.find("(")
        rp = s.find(")", lp)
        if lp == -1 or rp == -1 or "{" not in s[rp:]:
            continue
        ctx = raw_lines[idx].strip() if idx < len(raw_lines) else s
        argc = _count_args(s[lp + 1:rp])
        if argc > 4:
            issues.append(Issue(
                kind="too-many-args", file=fname, line=idx + 1,
                message=f"в этой функции {argc} аргументов — слишком много",
                suggestion="Собери аргументы в объект/структуру-параметры",
                severity="medium", context=ctx))
        brace = s.find("{", rp)
        abs_idx = line_starts[idx] + brace
        end_pos, inner_depth = _match_braces(stripped, abs_idx, line_starts)
        end_line = _line_of(end_pos, line_starts) if isinstance(end_pos, int) else idx
        span = end_line - idx
        if span > 50:
            issues.append(Issue(
                kind="long-function", file=fname, line=idx + 1,
                message=f"объявление ~{span} строк — функция слишком длинная",
                suggestion="Вынеси часть логики в отдельные функции с говорящими именами",
                severity="high", context=ctx))
        if inner_depth > 3:
            issues.append(Issue(
                kind="deep-nesting", file=fname, line=idx + 1,
                message=f"вложенность ~{inner_depth} уровней внутри функции",
                suggestion="Инвертируй условия и выходи раньше (guard clauses)",
                severity="high", context=ctx))
    return issues


def analyze_generic(path: str | Path) -> dict[str, Any]:
    """Анализ не-Python файла (JS/TS/Go/C++/Java/Kotlin/Rust) — эвристика."""
    p = Path(path)
    if not p.is_file():
        return {"file": str(p), "ok": False, "error": f"файл не найден: {p}"}
    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as e:
        return {"file": str(p), "ok": False, "error": f"не удалось прочитать: {e}"}
    stripped = _strip_code(text)
    raw_lines = text.splitlines()
    issues: list[Issue] = []

    for i, line in enumerate(stripped.splitlines(), 1):
        for m in _NUM.finditer(line):
            val = m.group(1)
            try:
                fv = float(val)
            except ValueError:
                continue
            if fv in _TRIVIAL:
                continue
            issues.append(Issue(
                kind="magic-number", file="", line=i,
                message=f"магическое число {val}",
                suggestion=f"Вынеси в именованную константу (NAME = {val})",
                severity="low",
                context=raw_lines[i - 1].strip() if i <= len(raw_lines) else ""))

    issues.extend(_duplicate_blocks(raw_lines))
    issues.extend(_scan_functions(stripped, raw_lines, str(p)))

    for issue in issues:
        issue.file = str(p)
    dicts = [i.to_dict() for i in issues]
    return {"file": str(p), "ok": True, "issues": dicts, "total": len(dicts),
            "score": score_of(dicts), "lang": "generic"}
