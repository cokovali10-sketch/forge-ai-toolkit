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
        # col_offset/end_col_offset — смещения в байтах UTF-8, поэтому режем
        # байты, а не символы (иначе строки с кириллицей ломаются).
        bl = lines[lineno - 1].encode("utf-8")
        for n in sorted(items, key=lambda x: x.col_offset, reverse=True):
            end = getattr(n, "end_col_offset", None)
            if end is None:
                continue
            bl = bl[:n.col_offset] + const_names[n.value].encode("utf-8") + bl[end:]
        lines[lineno - 1] = bl.decode("utf-8")

    insert_at = 0
    if (tree.body and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)):
        insert_at = tree.body[0].end_lineno or 0
    for n in tree.body:
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            insert_at = max(insert_at, n.end_lineno or 0)

    defs = ["# --- константы вынесены FORGE refactor ---\n"]
    defs += [f"{const_names[v]} = {v!r}\n" for v in sorted(repeated)]
    defs.append("\n")
    new_text = "".join(lines[:insert_at]) + "".join(defs) + "".join(lines[insert_at:])

    p.write_text(new_text, encoding="utf-8")
    return {"changed": True,
            "constants": {const_names[v]: v for v in sorted(repeated)},
            "occurrences": len(targets)}


def apply_unused_imports(path: str | Path) -> dict[str, Any]:
    """Удаляет неиспользуемые импорты (Python). Возвращает отчёт.

    Поведение не меняется: удаляются только имена, которые нигде не встречаются
    (в т.ч. в строках и `__all__`); многострочные импорты и `# noqa` не трогаем."""
    p = Path(path)
    if p.suffix.lower() != ".py":
        return {"changed": False, "reason": "авто-фикс пока только для Python"}
    text = p.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return {"changed": False, "reason": f"файл не парсится: {e}"}

    from forge.refactor.clean_code import collect_unused_imports
    plain = text.splitlines()
    groups = collect_unused_imports(tree, plain)
    if not groups:
        return {"changed": False, "reason": "нет неиспользуемых импортов"}

    lines = text.splitlines(keepends=True)
    removed: list[str] = []
    for stmt, names in sorted(groups, key=lambda g: -g[0].lineno):
        drop = set(names)
        keep = [a for a in stmt.names
                if (a.asname or (a.name.split(".")[0] if isinstance(stmt, ast.Import)
                                 else a.name)) not in drop]
        start = stmt.lineno - 1
        end = (getattr(stmt, "end_lineno", stmt.lineno) or stmt.lineno) - 1
        indent = re.match(r"[ \t]*", plain[stmt.lineno - 1]).group(0)
        if not keep:
            del lines[start:end + 1]
        else:
            alias = [(f"{a.name} as {a.asname}" if a.asname else a.name) for a in keep]
            if isinstance(stmt, ast.Import):
                rendered = "import " + ", ".join(alias)
            else:
                mod = "." * stmt.level + (stmt.module or "")
                rendered = f"from {mod} import " + ", ".join(alias)
            lines[start] = indent + rendered + "\n"
        removed.extend(names)

    p.write_text("".join(lines), encoding="utf-8")
    return {"changed": True, "removed_imports": sorted(set(removed))}


def apply(path: str | Path, test_cmd: list[str] | None = None,
          run_tests: bool = False, only: str | None = None) -> dict[str, Any]:
    """Применить безопасные фиксы с бэкапом, проверкой и авто-откатом.

    `only` позволяет выбрать один вид фикса: `"imports"` (мёртвые импорты) или
    `"constants"` (магические числа). `None` — оба."""
    p = Path(path)
    if not p.is_file():
        return {"ok": False, "changed": False, "error": f"файл не найден: {p}"}
    original = p.read_text(encoding="utf-8")
    backup = p.with_suffix(p.suffix + ".forgebak")
    backup.write_text(original, encoding="utf-8")

    fix_imports = (apply_unused_imports(p) if only in (None, "imports")
                   else {"changed": False})
    fix_magic = (apply_magic_constants(p) if only in (None, "constants")
                 else {"changed": False})
    if not (fix_imports.get("changed") or fix_magic.get("changed")):
        backup.unlink(missing_ok=True)
        reason = fix_magic.get("reason") or fix_imports.get("reason") or "нечего чинить"
        return {"ok": True, "changed": False, "reason": reason}

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
    out: dict[str, Any] = {"ok": True, "changed": True, "tests_returncode": tests_rc}
    if fix_magic.get("changed"):
        out["constants"] = fix_magic["constants"]
        out["occurrences"] = fix_magic["occurrences"]
    if fix_imports.get("changed"):
        out["removed_imports"] = fix_imports["removed_imports"]
    return out
