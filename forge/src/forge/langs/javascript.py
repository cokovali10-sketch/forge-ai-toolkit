"""JavaScript/TypeScript module: detect/lint/test/scaffold.

Линт — node --check (парсинг без выполнения). Node нет = честный WARNING,
а не FAIL: чужой комп не виноват, что тулчейна нет.
"""
from __future__ import annotations

import json as _json
from pathlib import Path
from typing import Any

from forge.core.result import ToolResult, timed
from forge.langs import base as _b

EXTS = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}
ID, TITLE = "javascript", "JavaScript/TypeScript"


def detect(root: str | Path) -> dict[str, Any]:
    base = Path(root)
    markers = [f for f in ("package.json", "package-lock.json", "yarn.lock",
                           "pnpm-lock.yaml", "tsconfig.json", ".nvmrc")
               if (base / f).is_file()]
    files = _b.collect(base, EXTS, 50)
    return {"present": bool(markers or files), "markers": markers,
            "files": len(files)}


def lint(root: str | Path) -> ToolResult:
    def run() -> dict:
        node = _b.which("node")
        if not node:
            return _b.missing_tool("node").result
        bad = []
        for f in _b.collect(root, EXTS):
            if f.suffix in (".ts", ".tsx") and not _b.which("tsc"):
                continue  # типы без tsc не проверяем — честно пропускаем
            r = _b.run([node, "--check", str(f)], root, 120)
            if not r["ok"]:
                bad.append(f"{f.name}: {r['log'][-300:]}")
        if bad:
            raise SyntaxError(f"{len(bad)} файлов с ошибками: {bad[:5]}")
        return {"files_checked": len(_b.collect(root, EXTS))}
    return timed(run)


def test(root: str | Path, timeout: int = 300) -> ToolResult:
    base = Path(root)
    try:
        pkg = _json.loads((base / "package.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ToolResult(status="SUCCESS", result={"ran": False},
                          warnings=["нет package.json — тестить нечего"])
    script = (pkg.get("scripts", {}) or {}).get("test", "")
    if not script or script.strip() in ("echo \"Error: no test specified\" && exit 1",):
        return ToolResult(status="SUCCESS", result={"ran": False},
                          warnings=["npm test не настроен"])
    npm = _b.which("npm")
    if not npm:
        return _b.missing_tool("npm")
    r = _b.run([npm, "test", "--silent"], base, timeout)
    if not r["ok"]:
        raise RuntimeError(f"npm test: {r['log'][-1500:]}")
    return ToolResult(status="SUCCESS", result={"ran": True, "log_tail": r["log"][-500:]})


def scaffold(name: str, out: str | Path) -> dict[str, Any]:
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in (name or "app")).lower() or "app"
    made = _b.write_tree(out, {
        "package.json": _json.dumps({"name": safe, "version": "0.1.0",
                                     "type": "module",
                                     "scripts": {"start": "node index.js",
                                                 "test": "node --test"}},
                                    indent=2) + "\n",
        "README.md": f"# {safe}\n",
        "index.js": f"console.log('hello from {safe}');\n",
        "index.test.js": "import test from 'node:test';\nimport assert from 'node:assert';\n\n"
                         "test('smoke', () => assert.ok(true));\n",
    })
    return {"created": made}
