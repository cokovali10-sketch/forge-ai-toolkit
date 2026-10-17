"""FORGE refactor: чистый код без изменения поведения.

Инструменты для ИИ-агентов, которые хотят улучшить существующий код:
- найти длинные функции (>50 строк) и предложить извлечь часть в новую функцию
- найти глубокую вложенность (>3 уровня) и предложить ранний выход (guard clauses)
- найти дубликаты блоков (3+ одинаковые строки) и предложить вынести в функцию
- найти «магические числа» и предложить именованные константы
- найти функции с большим числом аргументов (>4) и предложить объект-параметр
- найти «божественные» классы/файлы (>200 строк) и предложить разбить

Все рекомендации не меняют поведение программы — только структуру.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Issue:
    kind: str          # long-function, deep-nesting, duplicate-block, magic-number, too-many-args, god-class
    file: str
    line: int
    message: str
    suggestion: str
    severity: str      # low / medium / high
    context: str = ""  # исходный фрагмент кода (первая строка проблемы)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "suggestion": self.suggestion,
            "severity": self.severity,
            "context": self.context,
        }


def _complexity(fn: ast.AST) -> int:
    """Цикломатическая сложность функции: 1 + число точек ветвления.

    Не заходит во вложенные функции — у каждой своя сложность."""
    branch_types: tuple = (ast.If, ast.For, ast.AsyncFor, ast.While,
                           ast.ExceptHandler, ast.With, ast.AsyncWith,
                           ast.BoolOp, ast.IfExp, ast.comprehension, ast.Assert)
    match_type = getattr(ast, "Match", None)
    total = 1
    stack = list(getattr(fn, "body", []))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        if isinstance(node, branch_types) or (match_type and isinstance(node, match_type)):
            total += 1
        stack.extend(ast.iter_child_nodes(node))
    return total


_WEIGHTS = {"high": 5.0, "medium": 2.0, "low": 0.5}


def score_of(issues: list[dict[str, Any]], files: int = 1) -> int:
    """Оценка здоровья кода 0..100: 100 = чисто.

    Штраф взвешен по серьёзности и нормирован на число файлов, поэтому
    большой проект не обнуляется лишь оттого, что в нём много кода."""
    penalty = sum(_WEIGHTS.get(i.get("severity", ""), 0.0) for i in issues)
    per_file = penalty / max(1, files)
    return max(0, min(100, round(100 - per_file)))


class _FunctionVisitor(ast.NodeVisitor):
    """Собирает функции с их границами и количеством аргументов."""

    def __init__(self, source_lines: list[str]):
        self.lines = source_lines
        self.issues: list[Issue] = []
        self._depth = 0
        self._max_depth = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node, "функция")
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node, "функция")
        self.generic_visit(node)

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str) -> None:
        start = node.lineno
        end = getattr(node, "end_lineno", start)
        length = end - start + 1
        args_count = len(node.args.args)
        if args_count > 4:
            self.issues.append(Issue(
                kind="too-many-args",
                file="", line=start,
                message=f"'{node.name}': {args_count} аргументов — слишком много",
                suggestion="Собери аргументы в объект/конфиг (dataclass), чтобы сигнатура осталась короткой",
                severity="medium",
                context=self._line(start),
            ))
        if length > 50:
            self.issues.append(Issue(
                kind="long-function",
                file="", line=start,
                message=f"'{node.name}': {length} строк — функция слишком длинная",
                suggestion="Вынеси часть логики в отдельные функции с говорящими именами, оставив здесь только общий ход",
                severity="high",
                context=self._line(start),
            ))
        cc = _complexity(node)
        if cc > 10:
            self.issues.append(Issue(
                kind="high-complexity",
                file="", line=start,
                message=f"'{node.name}': цикломатическая сложность {cc} (>10)",
                suggestion="Разбей на функции по ветвям/случаям; вынеси условия в именованные предикаты",
                severity="high",
                context=self._line(start),
            ))

    def _line(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.lines):
            return self.lines[lineno - 1].strip()
        return ""

    def visit_For(self, node: ast.For) -> None:
        self._enter(node)
        self.generic_visit(node)
        self._depth -= 1

    def visit_While(self, node: ast.While) -> None:
        self._enter(node)
        self.generic_visit(node)
        self._depth -= 1

    def visit_If(self, node: ast.If) -> None:
        self._enter(node)
        self.generic_visit(node)
        self._depth -= 1

    def visit_With(self, node: ast.With) -> None:
        self._enter(node)
        self.generic_visit(node)
        self._depth -= 1

    def visit_Try(self, node: ast.Try) -> None:
        self._enter(node)
        self.generic_visit(node)
        self._depth -= 1

    def _enter(self, node: ast.AST) -> None:
        self._depth += 1
        self._max_depth = max(self._max_depth, self._depth)
        if self._depth > 3:
            self.issues.append(Issue(
                kind="deep-nesting",
                file="", line=node.lineno,
                message=f"вложенность {self._depth} уровней — читать сложно",
                suggestion="Вынеси внутреннее тело в отдельную функцию с ранним выходом (guard clauses)",
                severity="high",
                context=self._line(node.lineno),
            ))


class _ModuleVisitor(ast.NodeVisitor):
    """Собирает классы и их размер."""

    def __init__(self, source_lines: list[str]):
        self.lines = source_lines
        self.issues: list[Issue] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        start = node.lineno
        end = getattr(node, "end_lineno", start)
        length = end - start + 1
        if length > 200:
            self.issues.append(Issue(
                kind="god-class",
                file="", line=start,
                message=f"класс '{node.name}': {length} строк — слишком большой класс",
                suggestion="Разбей на несколько классов по ответственности (SRP)",
                severity="high",
                context=self._line(start),
            ))
        self.generic_visit(node)

    def _line(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.lines):
            return self.lines[lineno - 1].strip()
        return ""


def _magic_numbers(tree: ast.AST, lines: list[str]) -> list[Issue]:
    """Находит «магические числа» через AST — без ложных срабатываний в докстрингах."""
    trivial = {0, 1, 2, 10, 100, -1}
    issues: list[Issue] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        val = node.value
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            continue
        if val in trivial:
            continue
        line = getattr(node, "lineno", 0)
        issues.append(Issue(
            kind="magic-number",
            file="", line=line,
            message=f"магическое число {val}",
            suggestion=f"Вынеси в именованную константу (NAME = {val}) с описанием смысла",
            severity="low",
            context=lines[line - 1].strip() if 1 <= line <= len(lines) else "",
        ))
    return issues


def _duplicate_blocks(lines: list[str]) -> list[Issue]:
    """Находит дубликаты блоков из 3+ одинаковых подряд идущих непустых строк."""
    issues: list[Issue] = []
    seen: dict[str, tuple[int, int]] = {}
    cleaned = [(i, l.strip()) for i, l in enumerate(lines, 1) if l.strip()]
    n = len(cleaned)
    for size in (3, 4, 5):
        for i in range(n - size + 1):
            block = tuple(cleaned[i + j][1] for j in range(size))
            start_line = cleaned[i][0]
            key = "\n".join(block)
            if key in seen:
                first_i, first_line = seen[key]
                if i - first_i >= size:  # не перекрывающиеся блоки
                    issues.append(Issue(
                        kind="duplicate-block",
                        file="", line=start_line,
                        message=f"блок из {size} строк повторяется (сначала в строке {first_line})",
                        suggestion="Вынеси повторяющийся блок в отдельную функцию",
                        severity="medium",
                        context=cleaned[i][1],
                    ))
            else:
                seen[key] = (i, start_line)
    return issues


def _noqa_lines(lines: list[str]) -> set[int]:
    """Строки (1-based) с `# noqa` — такие импорты не трогаем."""
    return {i for i, line in enumerate(lines, 1) if "# noqa" in line}


def _local_name(node: ast.Import | ast.ImportFrom, a: ast.alias) -> str:
    if isinstance(node, ast.Import):
        return a.asname or a.name.split(".")[0]
    return a.asname or a.name


def collect_unused_imports(tree: ast.Module,
                           lines: list[str]) -> list[tuple[ast.stmt, list[str]]]:
    """Группирует неиспользуемые импорты по инструкции.

    Возвращает список `(узел, [локальные имена для удаления])`. Консервативно:
    однострочные инструкции без inline-комментариев/`# noqa`; имена, встречающиеся
    где-либо (в т.ч. в строках — `__all__`, докстринги), считаются использованными."""
    imported: dict[str, tuple[ast.stmt, ast.alias]] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for a in node.names:
                imported.setdefault(a.asname or a.name.split(".")[0], (node, a))
        elif isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                continue
            for a in node.names:
                if a.name == "*":
                    continue
                imported.setdefault(a.asname or a.name, (node, a))

    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            used.update(re.findall(r"\w+", node.value))

    skip = _noqa_lines(lines)
    groups: dict[int, tuple[ast.stmt, list[str]]] = {}
    for name, (stmt, _a) in imported.items():
        if name in used:
            continue
        start = stmt.lineno
        end = getattr(stmt, "end_lineno", start) or start
        if start != end or start in skip or end in skip:
            continue
        if "#" in (lines[start - 1] if 1 <= start <= len(lines) else ""):
            continue
        groups.setdefault(start, (stmt, []))[1].append(name)
    return list(groups.values())


def _unused_imports(tree: ast.Module, lines: list[str]) -> list[Issue]:
    """Неиспользуемые импорты — мёртвый код, который безопасно удалить."""
    issues: list[Issue] = []
    for stmt, names in collect_unused_imports(tree, lines):
        context = lines[stmt.lineno - 1].strip() if 1 <= stmt.lineno <= len(lines) else ""
        issues.append(Issue(
            kind="unused-import", file="", line=stmt.lineno,
            message=f"неиспользуемые импорты: {', '.join(sorted(names))}",
            suggestion="Удали их (forge refactor --apply сделает это сам безопасно)",
            severity="low", context=context))
    return issues


def _is_bool_or_none(value: Any) -> bool:
    # `is` вместо `in {}`: 1 == True, поэтому множество дало бы ложное срабатывание.
    return value is None or value is True or value is False


def _comparison_edits(tree: ast.Module, lines: list[str]) -> list[dict[str, Any]]:
    """Сравнения с None/True/False, которые PEP8 велит писать через `is`.

    Возвращает безопасные правки `{line, start, end, repl}` — смещения в байтах
    UTF-8 (как у `ast`), `repl` уже в байтах. Многострочные и неоднозначные
    (с комментарием между операндами) сравнения пропускаются."""
    edits: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare) or len(node.ops) != 1:
            continue
        op = node.ops[0]
        if not isinstance(op, (ast.Eq, ast.NotEq)) or not node.comparators:
            continue
        left = node.left
        right = node.comparators[0]
        const = None
        if isinstance(right, ast.Constant) and _is_bool_or_none(right.value):
            const = right
        elif isinstance(left, ast.Constant) and _is_bool_or_none(left.value):
            const = left
        if const is None:
            continue
        if left.end_lineno != right.lineno or left.end_col_offset is None:
            continue
        line_no = left.end_lineno
        start, end = left.end_col_offset, right.col_offset
        bl = lines[line_no - 1].encode("utf-8") if 1 <= line_no <= len(lines) else b""
        op_text = b"==" if isinstance(op, ast.Eq) else b"!="
        if bl[start:end].replace(b" ", b"").replace(b"\t", b"") != op_text:
            continue
        kw = b"is" if isinstance(op, ast.Eq) else b"is not"
        edits.append({"line": line_no, "start": start, "end": end,
                      "repl": b" " + kw + b" "})
    return edits


def _simplifiable_comparisons(tree: ast.Module, lines: list[str]) -> list[Issue]:
    """Сравнения `== None` / `!= True` и т.п. — переписываются в `is`/`is not`."""
    issues: list[Issue] = []
    for e in _comparison_edits(tree, lines):
        ln = e["line"]
        issues.append(Issue(
            kind="simplifiable-comparison", file="", line=ln,
            message="сравнение с None/True/False через == или !=",
            suggestion="Пиши через `is` / `is not` (PEP8; forge refactor --apply сделает сам)",
            severity="low",
            context=lines[ln - 1].strip() if 1 <= ln <= len(lines) else ""))
    return issues


DEFAULT_CODE_EXTS = (".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
                     ".go", ".cpp", ".cc", ".cxx", ".hpp", ".hh", ".h",
                     ".java", ".kt", ".rs")


def analyze_file(path: str | Path) -> dict[str, Any]:
    """Анализирует один файл. Python — через AST, остальные — эвристикой."""
    p = Path(path)
    if not p.is_file():
        return {"file": str(p), "ok": False, "error": f"файл не найден: {p}"}
    if p.suffix.lower() == ".py":
        return _analyze_python(p)
    from forge.refactor.generic import analyze_generic
    return analyze_generic(p)


def _analyze_python(p: Path) -> dict[str, Any]:
    """Анализ Python-файла через AST."""
    try:
        text = p.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as e:
        return {"file": str(p), "ok": False, "error": f"не удалось прочитать: {e}"}
    lines = text.splitlines()
    issues: list[Issue] = []

    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return {"file": str(p), "ok": False, "error": f"ошибка синтаксиса: {e}"}

    fv = _FunctionVisitor(lines)
    fv.visit(tree)
    issues.extend(fv.issues)

    mv = _ModuleVisitor(lines)
    mv.visit(tree)
    issues.extend(mv.issues)

    issues.extend(_magic_numbers(tree, lines))
    issues.extend(_duplicate_blocks(lines))
    issues.extend(_unused_imports(tree, lines))
    issues.extend(_simplifiable_comparisons(tree, lines))

    for issue in issues:
        issue.file = str(p)

    dicts = [i.to_dict() for i in issues]
    return {
        "file": str(p),
        "ok": True,
        "issues": dicts,
        "total": len(issues),
        "score": score_of(dicts),
    }


def analyze_dir(root: str | Path,
                exts: tuple[str, ...] = DEFAULT_CODE_EXTS) -> dict[str, Any]:
    """Рекурсивно анализирует директорию."""
    base = Path(root)
    results: list[dict[str, Any]] = []
    total = 0
    all_issues: list[dict[str, Any]] = []
    for fp in sorted(base.rglob("*")):
        if fp.is_file() and fp.suffix.lower() in exts:
            if any(skip in fp.parts for skip in (".git", ".venv", "venv", "__pycache__", "node_modules")):
                continue
            res = analyze_file(fp)
            results.append(res)
            total += res["total"]
            all_issues.extend(res.get("issues", []))
    return {"root": str(root), "files": len(results), "total_issues": total,
            "score": score_of(all_issues, len(results)), "files_analyzed": results}


_KIND_EFFORT = {
    "magic-number": "S",
    "duplicate-block": "S",
    "unused-import": "S",
    "simplifiable-comparison": "S",
    "too-many-args": "M",
    "deep-nesting": "M",
    "high-complexity": "M",
    "long-function": "L",
    "god-class": "L",
}
_SEV_ORDER = {"high": 0, "medium": 1, "low": 2}


def make_plan(result: dict[str, Any]) -> dict[str, Any]:
    """Превращает результат inspect в приоритетный план шагов рефакторинга.

    Шаги отсортированы: сначала серьёзные (high), затем по дешевизне усилия
    (S → M → L), затем по файлу и строке. Это порядок «что чинить первым»."""
    entries: list[tuple[str, list[dict[str, Any]]]] = []
    if result.get("files_analyzed") is not None:
        entries = [(f.get("file", ""), f.get("issues", []))
                   for f in result["files_analyzed"]]
    else:
        entries = [(result.get("file", ""), result.get("issues", []))]

    items: list[dict[str, Any]] = []
    for fname, issues in entries:
        for i in issues:
            items.append({**i, "file": fname,
                          "effort": _KIND_EFFORT.get(i.get("kind", ""), "M")})
    effort_rank = {"S": 0, "M": 1, "L": 2}
    items.sort(key=lambda x: (_SEV_ORDER.get(x.get("severity", ""), 3),
                              effort_rank.get(x.get("effort", "M"), 1),
                              x.get("file", ""), x.get("line", 0)))
    steps = [{"order": n, "severity": i["severity"], "kind": i["kind"],
              "effort": i["effort"], "file": i["file"], "line": i.get("line", 0),
              "message": i.get("message", ""), "suggestion": i.get("suggestion", "")}
             for n, i in enumerate(items, 1)]
    return {"root": result.get("root") or result.get("file", ""),
            "score": result.get("score", 100),
            "total": len(steps), "steps": steps}
