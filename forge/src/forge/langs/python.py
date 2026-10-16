"""Python module: detect/lint/test/scaffold. Тулчейн — сам Python (всегда есть)."""
from __future__ import annotations

import py_compile
from pathlib import Path
from typing import Any

from forge.core.result import ToolResult, timed
from forge.langs import base as _b

EXTS = {".py"}
ID, TITLE = "python", "Python"


def detect(root: str | Path) -> dict[str, Any]:
    base = Path(root)
    markers = [f for f in ("pyproject.toml", "requirements.txt", "setup.py",
                           "setup.cfg", "Pipfile", "poetry.lock")
               if (base / f).is_file()]
    files = _b.collect(base, EXTS, 50)
    return {"present": bool(markers or files), "markers": markers,
            "files": len(files)}


def lint(root: str | Path) -> ToolResult:
    def run() -> dict:
        files = _b.collect(root, EXTS)
        bad = []
        for f in files:
            try:
                py_compile.compile(str(f), doraise=True)
            except py_compile.PyCompileError as e:
                bad.append(f"{f.name}: {e.msg.splitlines()[0] if e.msg else e}")
        if bad:
            raise SyntaxError(f"{len(bad)} файлов с ошибками: {bad[:5]}")
        return {"files_checked": len(files)}
    return timed(run)


def test(root: str | Path, timeout: int = 300) -> ToolResult:
    base = Path(root)
    has = any(base.rglob(p) for p in ("tests", "test", "conftest.py")) or \
        list(base.glob("test_*.py"))
    if not has:
        return ToolResult(status="SUCCESS", result={"ran": False},
                          warnings=["тестов не найдено (tests/, test_*.py)"])
    py = _b.which("python") or "python"
    r = _b.run([py, "-m", "pytest", "-q"], base, timeout)
    if r["code"] == 127 or "No module named pytest" in r["log"]:
        return ToolResult(status="SUCCESS", result={"ran": False},
                          warnings=["pytest не установлен"])
    if not r["ok"]:
        raise RuntimeError(f"pytest failed: {r['log'][-1500:]}")
    return ToolResult(status="SUCCESS",
                      result={"ran": True, "log_tail": r["log"][-500:]},
                      duration_ms=0)


def scaffold(name: str, out: str | Path) -> dict[str, Any]:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name) or "app"
    made = _b.write_tree(out, {
        "pyproject.toml": f"[project]\nname = \"{safe}\"\nversion = \"0.1.0\"\n"
                          f"requires-python = \">=3.10\"\n",
        "README.md": f"# {safe}\n",
        "main.py": "def main() -> None:\n    print(\"hello from "
                   + safe + "\")\n\n\nif __name__ == \"__main__\":\n    main()\n",
        "test_main.py": "from main import main\n\n\n"
                        "def test_main(capsys):\n    main()\n"
                        "    assert \"hello\" in capsys.readouterr().out\n",
    })
    return {"created": made}
