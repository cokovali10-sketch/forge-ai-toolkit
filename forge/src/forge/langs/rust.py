"""Rust module: detect/lint/test/scaffold. cargo check/test, fmt как warning."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from forge.core.result import ToolResult, timed
from forge.langs import base as _b

EXTS = {".rs"}
ID, TITLE = "rust", "Rust"


def detect(root: str | Path) -> dict[str, Any]:
    base = Path(root)
    markers = [f for f in ("Cargo.toml", "Cargo.lock", "rust-toolchain.toml")
               if (base / f).is_file()]
    files = _b.collect(base, EXTS, 50)
    return {"present": bool(markers or files), "markers": markers,
            "files": len(files)}


def lint(root: str | Path) -> ToolResult:
    def run() -> dict:
        if not _b.which("cargo"):
            return {"files_checked": 0, "no_toolchain": "cargo"}
        base = Path(root)
        if not (base / "Cargo.toml").is_file():
            return {"files_checked": 0, "note": "нет Cargo.toml"}
        r = _b.run(["cargo", "check", "--quiet"], base, 600)
        if not r["ok"]:
            raise RuntimeError(f"cargo check: {r['log'][-1500:]}")
        fmt = _b.run(["cargo", "fmt", "--check"], base, 120)
        out = {"files_checked": len(_b.collect(base, EXTS))}
        if not fmt["ok"]:
            out["unformatted"] = True
        return out
    r = timed(run)
    if r.ok and isinstance(r.result, dict):
        if r.result.get("no_toolchain"):
            r.warnings = [f"нет тулчейна ({r.result['no_toolchain']}) — проверка пропущена"]
        elif r.result.get("unformatted"):
            r.warnings = ["cargo fmt: есть неотформатированное"]
    return r


def test(root: str | Path, timeout: int = 600) -> ToolResult:
    base = Path(root)
    if not _b.which("cargo"):
        return _b.missing_tool("cargo")
    if not (base / "Cargo.toml").is_file():
        return ToolResult(status="SUCCESS", result={"ran": False},
                          warnings=["нет Cargo.toml — тестить нечего"])
    r = _b.run(["cargo", "test", "--quiet"], base, timeout)
    if not r["ok"]:
        raise RuntimeError(f"cargo test: {r['log'][-1500:]}")
    return ToolResult(status="SUCCESS", result={"ran": True, "log_tail": r["log"][-500:]})


def scaffold(name: str, out: str | Path) -> dict[str, Any]:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (name or "app")).lower() or "app"
    made = _b.write_tree(out, {
        "Cargo.toml": f"[package]\nname = \"{safe}\"\nversion = \"0.1.0\"\n"
                      f"edition = \"2021\"\n",
        ".gitignore": "/target\n",
        "README.md": f"# {safe}\n",
        "src/main.rs": f"fn main() {{\n    println!(\"hello from {safe}\");\n}}\n",
    })
    return {"created": made}
