"""C++ module: detect/lint/test/scaffold. g++ -fsyntax-only, без сборки."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from forge.core.result import ToolResult, timed
from forge.langs import base as _b

EXTS = {".cpp", ".hpp", ".cc", ".hh", ".c", ".h"}
ID, TITLE = "cpp", "C++"


def detect(root: str | Path) -> dict[str, Any]:
    base = Path(root)
    markers = [f for f in ("CMakeLists.txt", "Makefile", "meson.build",
                           "conanfile.txt", "vcpkg.json") if (base / f).is_file()]
    files = _b.collect(base, EXTS, 50)
    return {"present": bool(markers or files), "markers": markers,
            "files": len(files)}


def _compiler() -> str:
    for c in ("g++", "clang++", "cl"):
        if _b.which(c):
            return c
    return ""


def lint(root: str | Path) -> ToolResult:
    def run() -> dict:
        cc = _compiler()
        if not cc:
            return _b.missing_tool("g++/clang++").result
        bad = []
        for f in _b.collect(root, EXTS):
            if f.suffix in (".h", ".hpp", ".hh"):
                continue  # заголовки проверяются через .cpp (включение)
            r = _b.run([cc, "-fsyntax-only", "-std=c++17", str(f)], root, 180)
            if not r["ok"]:
                bad.append(f"{f.name}: {r['log'][-300:]}")
        if bad:
            raise SyntaxError(f"{len(bad)} файлов с ошибками: {bad[:5]}")
        return {"files_checked": len(_b.collect(root, EXTS)), "compiler": cc}
    return timed(run)


def test(root: str | Path, timeout: int = 300) -> ToolResult:
    base = Path(root)
    if (base / "build" / "CTestTestfile.cmake").is_file() and _b.which("ctest"):
        r = _b.run(["ctest", "--output-on-failure"], base / "build", timeout)
        if not r["ok"]:
            raise RuntimeError(f"ctest: {r['log'][-1500:]}")
        return ToolResult(status="SUCCESS", result={"ran": True, "log_tail": r["log"][-500:]})
    return ToolResult(status="SUCCESS", result={"ran": False},
                      warnings=["нет собранных тестов (build/CTestTestfile.cmake)"])


def scaffold(name: str, out: str | Path) -> dict[str, Any]:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (name or "app")) or "app"
    made = _b.write_tree(out, {
        "CMakeLists.txt": "cmake_minimum_required(VERSION 3.20)\n"
                          f"project({safe} CXX)\n"
                          "set(CMAKE_CXX_STANDARD 17)\n"
                          "add_executable(app main.cpp)\n",
        "README.md": f"# {safe}\n\ncmake -S . -B build && cmake --build build\n",
        "main.cpp": "#include <iostream>\n\nint main() {\n"
                    f"    std::cout << \"hello from {safe}\" << std::endl;\n}}\n",
    })
    return {"created": made}
