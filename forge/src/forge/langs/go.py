"""Go module: detect/lint/test/scaffold. gofmt + vet + test (тулчейн реален)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from forge.core.result import ToolResult, timed
from forge.langs import base as _b

EXTS = {".go"}
ID, TITLE = "go", "Go"


def detect(root: str | Path) -> dict[str, Any]:
    base = Path(root)
    markers = [f for f in ("go.mod", "go.sum", "go.work") if (base / f).is_file()]
    files = _b.collect(base, EXTS, 50)
    return {"present": bool(markers or files), "markers": markers,
            "files": len(files)}


def lint(root: str | Path) -> ToolResult:
    def run() -> dict:
        if not _b.which("go"):
            return _b.missing_tool("go").result
        files = _b.collect(root, EXTS)
        fmt = _b.run(["gofmt", "-l", "."], root, 120)
        unformatted = [l for l in fmt["log"].splitlines() if l.strip()]
        vet = _b.run(["go", "vet", "./..."], root, 300) if (Path(root) / "go.mod").is_file() else {"ok": True, "log": ""}
        if not vet["ok"]:
            raise RuntimeError(f"go vet: {vet['log'][-1500:]}")
        out = {"files_checked": len(files), "unformatted": unformatted[:10]}
        return out
    r = timed(run)
    if r.ok and isinstance(r.result, dict) and r.result.get("unformatted"):
        r.warnings = [f"gofmt: {len(r.result['unformatted'])} файлов не отформатированы"]
    return r


def test(root: str | Path, timeout: int = 300) -> ToolResult:
    if not _b.which("go"):
        return _b.missing_tool("go")
    if not (Path(root) / "go.mod").is_file():
        return ToolResult(status="SUCCESS", result={"ran": False},
                          warnings=["нет go.mod — тестить нечего"])
    r = _b.run(["go", "test", "./..."], root, timeout)
    if not r["ok"]:
        raise RuntimeError(f"go test: {r['log'][-1500:]}")
    return ToolResult(status="SUCCESS", result={"ran": True, "log_tail": r["log"][-500:]})


def scaffold(name: str, out: str | Path) -> dict[str, Any]:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (name or "app")).lower() or "app"
    made = _b.write_tree(out, {
        "go.mod": f"module {safe}\n\ngo 1.21\n",
        "README.md": f"# {safe}\n",
        "main.go": "package main\n\nimport \"fmt\"\n\nfunc main() {\n"
                   f"\tfmt.Println(\"hello from {safe}\")\n}}\n",
        "main_test.go": "package main\n\nimport \"testing\"\n\nfunc TestMain(t *testing.T) {\n\tmain()\n}\n",
    })
    return {"created": made}
