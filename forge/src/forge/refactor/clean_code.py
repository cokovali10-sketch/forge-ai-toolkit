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

    def _line(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.lines):
            return self.lines[lineno - 1].strip()
        return ""

    def visit_For(self, node: ast.For) -> None:
        self._check_depth(node, "for")
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self._check_depth(node, "while")
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        self._check_depth(node, "if")
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self._check_depth(node, "with")
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        self._check_depth(node, "try")
        self.generic_visit(node)

    def _check_depth(self, node: ast.AST, kind: str) -> None:
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
        self.generic_visit(node)
        self._depth -= 1


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


def analyze_file(path: str | Path) -> dict[str, Any]:
    """Анализирует один Python-файл и возвращает список проблем."""
    p = Path(path)
    if not p.is_file():
        return {"file": str(p), "ok": False, "error": f"файл не найден: {p}"}
    try:
        text = p.read_text(encoding="utf-8")
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

    for issue in issues:
        issue.file = str(p)

    return {
        "file": str(p),
        "ok": True,
        "issues": [i.to_dict() for i in issues],
        "total": len(issues),
    }


def analyze_dir(root: str | Path, exts: tuple[str, ...] = (".py",)) -> dict[str, Any]:
    """Рекурсивно анализирует директорию."""
    base = Path(root)
    results: list[dict[str, Any]] = []
    total = 0
    for fp in sorted(base.rglob("*")):
        if fp.is_file() and fp.suffix.lower() in exts:
            if any(skip in fp.parts for skip in (".git", ".venv", "venv", "__pycache__", "node_modules")):
                continue
            results.append(analyze_file(fp))
            total += results[-1]["total"]
    return {"root": str(root), "files": len(results), "total_issues": total, "files_analyzed": results}
