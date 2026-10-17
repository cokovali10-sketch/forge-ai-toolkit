"""FORGE refactor apply: безопасные авто-фиксы (поведение не меняется).

Первый и самый надёжный фикс: повторяющиеся «магические числа» в Python-файле
выносятся в именованные модульные константы. Значение сохраняется бит-в-бит,
поэтому поведение программы не меняется.

Гарантии безопасности:
- перед правкой делается резервная копия `<файл>.forgebak`;
- после правки файл парсится AST и компилируется (py_compile);
- при желании прогоняются тесты проекта;
- если что-то падает — файл возвращается из копии (авто-откат).

Имена автоматических констант намеренно простые (`CONST_<значение>`) — агенту
рядом с этим стоит переименовать их осмысленно (skill refactor-expert).
"""
from __future__ import annotations

import ast
import py_compile
import re
from pathlib import Path
from typing import Any

_TRIVIAL = {0, 1, 2, 10, 100, -1}


def _const_name(value: float) -> str:
    if isinstance(value, float):
        raw = f"{value:g}".replace("-", "neg").replace(".", "_")
    else:
        raw = str(value).replace("-", "neg")
    raw = re.sub(r"\W", "_", raw)
    return f"CONST_{raw}"


def _existing_toplevel_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                names.add((a.asname or a.name).split(".")[0])
    return names


def apply_magic_constants(path: str | Path) -> dict[str, Any]:
    """Выносит повторяющиеся магические числа в константы. Возвращает отчёт."""
    p = Path(path)
    if p.suffix.lower() != ".py":
        return {"changed": False, "reason": "авто-фикс пока только для Python"}
    text = p.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return {"changed": False, "reason": f"файл не парсится: {e}"}

    nodes: list[ast.Constant] = []
    counts: dict[float, int] = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and not isinstance(node.value, bool)
                and isinstance(node.value, (int, float))
                and node.value not in _TRIVIAL):
            nodes.append(node)
            counts[node.value] = counts.get(node.value, 0) + 1

    repeated = {v for v, c in counts.items() if c >= 2}
    if not repeated:
        return {"changed": False, "reason": "нет повторяющихся магических чисел"}

    used = _existing_toplevel_names(tree)
    const_names: dict[float, str] = {}
    for value in sorted(repeated):
        name = _const_name(value)
        base = name
        i = 2
        while name in used:
            name = f"{base}_{i}"
            i += 1
        used.add(name)
        const_names[value] = name

    targets = [n for n in nodes if n.value in repeated]
    by_line: dict[int, list[ast.Constant]] = {}
    for n in targets:
        by_line.setdefault(n.lineno, []).append(n)

    lines = text.splitlines(keepends=True)
    for lineno, items in by_line.items():
        line = lines[lineno - 1]
        for n in sorted(items, key=lambda x: x.col_offset, reverse=True):
            end = getattr(n, "end_col_offset", None)
            if end is None:
                continue
            line = line[:n.col_offset] + const_names[n.value] + line[end:]
        lines[lineno - 1] = line

    insert_at = 0
    if (tree.body and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)):
        insert_at = tree.body[0].end_lineno or 0
    for n in tree.body:
        if isinstance(n, ast.ImportFrom) and n.module == "__future__":
            insert_at = max(insert_at, n.end_lineno or 0)

    defs = ["# --- константы вынесены FORGE refactor ---\n"]
    defs += [f"{const_names[v]} = {v!r}\n" for v in sorted(repeated)]
    defs.append("\n")
    new_text = "".join(lines[:insert_at]) + "".join(defs) + "".join(lines[insert_at:])

    p.write_text(new_text, encoding="utf-8")
    return {"changed": True,
            "constants": {const_names[v]: v for v in sorted(repeated)},
            "occurrences": len(targets)}


def apply(path: str | Path, test_cmd: list[str] | None = None,
          run_tests: bool = False) -> dict[str, Any]:
    """Применить безопасные фиксы с бэкапом, проверкой и авто-откатом."""
    p = Path(path)
    if not p.is_file():
        return {"ok": False, "changed": False, "error": f"файл не найден: {p}"}
    original = p.read_text(encoding="utf-8")
    backup = p.with_suffix(p.suffix + ".forgebak")
    backup.write_text(original, encoding="utf-8")

    fix = apply_magic_constants(p)
    if not fix.get("changed"):
        backup.unlink(missing_ok=True)
        return {"ok": True, "changed": False, "reason": fix.get("reason", "")}

    def rollback(reason: str, extra: dict | None = None) -> dict[str, Any]:
        p.write_text(original, encoding="utf-8")
        backup.unlink(missing_ok=True)
        out = {"ok": False, "changed": False, "error": reason}
        if extra:
            out.update(extra)
        return out

    try:
        ast.parse(p.read_text(encoding="utf-8"))
        py_compile.compile(str(p), doraise=True)
    except Exception as e:  # noqa: BLE001
        return rollback(f"проверка синтаксиса не прошла, откат: {e}")

    tests_rc = None
    if run_tests and test_cmd:
        import subprocess
        try:
            r = subprocess.run(test_cmd, cwd=str(p.parent), capture_output=True,
                               text=True, timeout=600)
        except (OSError, subprocess.SubprocessError) as e:
            return rollback(f"тесты не запустились, откат: {e}")
        tests_rc = r.returncode
        if r.returncode != 0:
            tail = ((r.stdout or "") + (r.stderr or ""))[-2000:]
            return rollback("тесты упали, откат", {"tests_returncode": tests_rc,
                                                   "output_tail": tail})

    backup.unlink(missing_ok=True)
    return {"ok": True, "changed": True, "constants": fix["constants"],
            "occurrences": fix["occurrences"], "tests_returncode": tests_rc}
