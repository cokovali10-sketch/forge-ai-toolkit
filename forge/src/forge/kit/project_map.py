"""FORGE map: карта проекта без запуска чего-либо.

Даёт агенту мгновенную картину чужого проекта:
- языки и строки кода (LOC) по каждому;
- файлы сборки и предполагаемые точки входа;
- самые крупные файлы;
- граф внутренних импортов Python + внешние зависимости.

Только чтение, ничего не исполняет, гигантские деревья ограничены `max_files`.
"""
from __future__ import annotations

import ast
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist",
        "build", "target", "out", ".gradle", ".idea", ".mypy_cache",
        ".pytest_cache", ".tox", "vendor"}

LANG = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript",
    ".mjs": "javascript", ".cjs": "javascript", ".ts": "typescript",
    ".tsx": "typescript", ".go": "go", ".rs": "rust", ".java": "java",
    ".kt": "kotlin", ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp",
    ".hpp": "cpp", ".hh": "cpp", ".h": "c", ".c": "c", ".cs": "csharp",
    ".rb": "ruby", ".php": "php", ".swift": "swift", ".scala": "scala",
    ".css": "css", ".scss": "css", ".html": "html", ".vue": "vue",
    ".sql": "sql", ".sh": "shell", ".yml": "yaml", ".yaml": "yaml",
    ".json": "json", ".toml": "toml", ".md": "markdown",
}

BUILD_FILES = ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
               "Pipfile", "package.json", "go.mod", "Cargo.toml",
               "build.gradle", "build.gradle.kts", "pom.xml", "Makefile",
               "CMakeLists.txt", "Dockerfile", "docker-compose.yml",
               "compose.yml", "tsconfig.json")

ENTRY_HINTS = ("main.py", "__main__.py", "app.py", "cli.py", "manage.py",
               "wsgi.py", "asgi.py", "index.js", "index.mjs", "index.ts",
               "server.js", "server.ts", "app.js", "app.ts", "main.go",
               "main.rs", "Main.java", "App.kt", "App.tsx", "index.html")

_ENTRY_RANK = ("main.py", "__main__.py", "main.go", "main.rs", "index.js",
               "index.ts", "server.js", "server.ts", "app.py")


def _iter_files(root: Path, max_files: int) -> list[Path]:
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in SKIP and not d.startswith("."))
        for fn in sorted(filenames):
            out.append(Path(dirpath) / fn)
            if len(out) >= max_files:
                return out
    return out


def _count_lines(p: Path) -> int:
    try:
        with p.open("r", encoding="utf-8-sig", errors="ignore") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def _py_modules(root: Path, files: list[Path]) -> dict[str, str]:
    """name -> относительный путь для всех .py (в т.ч. пакеты)."""
    mods: dict[str, str] = {}
    for p in files:
        if p.suffix.lower() != ".py":
            continue
        try:
            rel = p.relative_to(root)
        except ValueError:
            continue
        if rel.name == "__init__.py":
            name = ".".join(rel.parent.parts)
        else:
            name = ".".join(rel.with_suffix("").parts)
        if name:
            mods[name] = str(rel).replace("\\", "/")
    return mods


def _resolve(name: str, mods: dict[str, str]) -> str:
    """Известный модуль, совпадающий с target (в т.ч. как суффикс пакета).

    Понимает как `from forge.core.result import x` (когда проект лежит выше
    пакета), так и обратный случай, когда модуль записан длиннее импорта."""
    if name in mods:
        return name
    best = ""
    for mod in mods:
        if name.endswith("." + mod) or ("." in name and mod.endswith("." + name)):
            if len(mod) > len(best):
                best = mod
    return best


def _py_import_graph(root: Path, files: list[Path],
                     mods: dict[str, str]) -> dict[str, Any]:
    stdlib = getattr(sys, "stdlib_module_names", frozenset())
    edges: list[dict[str, str]] = []
    external: Counter = Counter()
    seen: set[tuple[str, str]] = set()
    for p in files:
        if p.suffix.lower() != ".py":
            continue
        try:
            rel = p.relative_to(root)
        except ValueError:
            continue
        src = (".".join(rel.parent.parts) if rel.name == "__init__.py"
               else ".".join(rel.with_suffix("").parts))
        try:
            tree = ast.parse(p.read_text(encoding="utf-8-sig"))
        except (OSError, SyntaxError, UnicodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if not name:
                    continue
                target = _resolve(name, mods)
                if target and target != src:
                    key = (src, target)
                    if key not in seen:
                        seen.add(key)
                        edges.append({"from": src, "to": target})
                elif not target:
                    top = name.split(".")[0]
                    if top and top not in stdlib and top != src.split(".")[0]:
                        external[top] += 1
    edges.sort(key=lambda e: (e["from"], e["to"]))
    return {"edges": edges, "modules": len(mods),
            "external_deps": [d for d, _ in external.most_common(20)]}


def build_map(root: str | Path, max_files: int = 20000) -> dict[str, Any]:
    """Строит карту проекта. Только чтение."""
    base = Path(root)
    if not base.is_dir():
        return {"ok": False, "error": f"не директория: {base}"}
    files = _iter_files(base, max_files)
    lang_files: Counter = Counter()
    lang_loc: Counter = Counter()
    sizes: list[tuple[int, str]] = []
    for p in files:
        lang = LANG.get(p.suffix.lower())
        if not lang:
            continue
        loc = _count_lines(p)
        lang_files[lang] += 1
        lang_loc[lang] += loc
        sizes.append((loc, str(p.relative_to(base)).replace("\\", "/")))
    sizes.sort(reverse=True)
    entries = [str(p.relative_to(base)).replace("\\", "/")
               for p in files if p.name in ENTRY_HINTS]
    entries.sort(key=lambda r: (_ENTRY_RANK.index(Path(r).name)
                                if Path(r).name in _ENTRY_RANK else len(_ENTRY_RANK),
                                len(r)))
    build = [f for f in BUILD_FILES if (base / f).is_file()]
    mods = _py_modules(base, files)
    graph = _py_import_graph(base, files, mods)
    code_loc = sum(lang_loc[l] for l in lang_loc if l not in
                   ("markdown", "json", "yaml", "toml", "css", "html"))
    languages = [{"lang": l, "files": lang_files[l], "loc": lang_loc[l]}
                 for l in sorted(lang_loc, key=lambda x: -lang_loc[x])]
    return {
        "ok": True,
        "root": str(base),
        "total_files": len(files),
        "total_loc": sum(lang_loc.values()),
        "code_loc": code_loc,
        "languages": languages,
        "build_files": build,
        "entry_points": entries[:12],
        "largest": [{"loc": n, "file": f} for n, f in sizes[:12]],
        "imports": graph,
    }


def render_text(m: dict[str, Any]) -> str:
    """Человекочитаемая карта (для CLI)."""
    if not m.get("ok"):
        return f"map: {m.get('error')}"
    lines = [f"FORGE map: {m['root']}",
             f"  файлов: {m['total_files']}  строк всего: {m['total_loc']}  "
             f"кода: {m['code_loc']}", ""]
    lines.append("Языки:")
    for it in m["languages"][:12]:
        lines.append(f"  {it['lang']:<12} {it['loc']:>8} строк  "
                     f"({it['files']} файлов)")
    if m["build_files"]:
        lines += ["", "Сборка: " + ", ".join(m["build_files"])]
    if m["entry_points"]:
        lines += ["", "Точки входа: " + ", ".join(m["entry_points"][:6])]
    if m["largest"]:
        lines += ["", "Крупнейшие файлы:"]
        for it in m["largest"][:6]:
            lines.append(f"  {it['loc']:>8}  {it['file']}")
    imp = m.get("imports", {})
    if imp.get("edges"):
        lines += ["", f"Внутренние импорты: {len(imp['edges'])} связей, "
                      f"{imp['modules']} модулей"]
    if imp.get("external_deps"):
        lines += ["", "Внешние зависимости: " + ", ".join(imp["external_deps"][:12])]
    return "\n".join(lines)
