"""Benchmark harness (prompt section 18): reproducible tasks + checks.

Honest scope: the harness executes CHECKS against a candidate output dir
and reports PASS/FAIL with evidence. Which AGENT produced the output
(model with/without FORGE) is recorded, never assumed. Comparing modes
requires a model; without one, the harness is validated by running it
against known-good and known-bad fixtures (must PASS and FAIL).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CheckResult:
    check: str
    ok: bool
    detail: str = ""
    ms: int = 0


@dataclass
class TaskResult:
    task: str
    agent: str
    passed: bool
    checks: list[CheckResult] = field(default_factory=list)
    ms: int = 0


def _run(cmd: list[str], cwd: Path, timeout: int) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, cwd=str(cwd))
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "[TIMEOUT]"
    except FileNotFoundError:
        return 127, f"missing executable: {cmd[0]}"


def check_exists(root: Path, spec: dict) -> CheckResult:
    t = time.time()
    p = root / spec["path"]
    ok = p.is_file() if spec.get("type", "file") == "file" else p.exists()
    return CheckResult(f"exists:{spec['path']}", ok,
                       "" if ok else "missing", int((time.time() - t) * 1000))


def check_contains(root: Path, spec: dict) -> CheckResult:
    t = time.time()
    p = root / spec["path"]
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return CheckResult(f"contains:{spec['path']}", False, str(e)[:200])
    ok = re.search(spec["regex"], text) is not None
    return CheckResult(f"contains:{spec['path']}:{spec['regex'][:40]}", ok,
                       "" if ok else "pattern not found",
                       int((time.time() - t) * 1000))


def check_json_valid(root: Path, spec: dict) -> CheckResult:
    t = time.time()
    try:
        json.loads((root / spec["path"]).read_text(encoding="utf-8"))
        return CheckResult(f"json:{spec['path']}", True, "",
                           int((time.time() - t) * 1000))
    except Exception as e:
        return CheckResult(f"json:{spec['path']}", False,
                           f"{type(e).__name__}: {e}"[:200],
                           int((time.time() - t) * 1000))


def check_pytest(root: Path, spec: dict) -> CheckResult:
    t = time.time()
    code, out = _run([sys.executable, "-m", "pytest", "-q"],
                     root, int(spec.get("timeout", 300)))
    ok = code == 0 and ("passed" in out)
    tail = "\n".join(out.splitlines()[-4:])
    return CheckResult("pytest", ok, "" if ok else tail[:600],
                       int((time.time() - t) * 1000))


def check_javac(root: Path, spec: dict) -> CheckResult:
    t = time.time()
    import os as _os
    import shutil as _sh
    import tempfile
    javac = _os.path.expandvars(spec.get("javac", "javac"))
    javac = re.sub(r"\$([A-Za-z_][A-Za-z0-9_]*)",
                   lambda m: _os.environ.get(m.group(1), m.group(0)), javac)
    if "/" not in javac.replace("\\", "/") and _sh.which(javac) is None:
        return CheckResult("javac", False, "SKIP: javac not on PATH",
                           int((time.time() - t) * 1000))
    files = sorted(root.rglob(spec.get("glob", "*.java")))
    if not files:
        return CheckResult("javac", False, "no sources found")
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [javac, "-encoding", "UTF-8",
               "-d", tmp]
        if spec.get("classpath"):
            cmd += ["-cp", spec["classpath"]]
        cmd += [str(f) for f in files]
        code, out = _run(cmd, root, int(spec.get("timeout", 300)))
    ok = code == 0
    return CheckResult("javac", ok, "" if ok else out[-600:],
                       int((time.time() - t) * 1000))


CHECKS = {"exists": check_exists, "contains": check_contains,
          "json_valid": check_json_valid, "pytest": check_pytest,
          "javac": check_javac}


def load_task(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_task(task: dict, candidate: str | Path, agent: str = "unknown") -> TaskResult:
    t = time.time()
    root = Path(candidate)
    results = []
    for spec in task.get("checks", []):
        fn = CHECKS.get(spec.get("type", ""))
        if fn is None:
            results.append(CheckResult(str(spec.get("type")), False,
                                       "unknown check type"))
            continue
        try:
            results.append(fn(root, spec))
        except Exception as e:
            results.append(CheckResult(str(spec.get("type")), False,
                                       f"{type(e).__name__}: {e}"))
    passed = bool(results) and all(r.ok for r in results)
    return TaskResult(task.get("id", "?"), agent, passed, results,
                      int((time.time() - t) * 1000))


def run_suite(tasks_dir: str | Path, candidate: str | Path,
              agent: str = "unknown") -> dict:
    results = []
    for f in sorted(Path(tasks_dir).glob("*.json")):
        results.append(run_task(load_task(f), candidate, agent))
    passed = sum(1 for r in results if r.passed)
    return {"agent": agent, "total": len(results), "passed": passed,
            "failed": len(results) - passed,
            "results": [{"task": r.task, "passed": r.passed,
                         "checks": [{"check": c.check, "ok": c.ok,
                                     "detail": c.detail} for c in r.checks]}
                        for r in results]}
