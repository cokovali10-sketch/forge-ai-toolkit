"""Unit test runners. Parses real results; never invents them."""
from __future__ import annotations

import glob
import os
import xml.etree.ElementTree as ET
from pathlib import Path

from .build import _run


def run_gradle_tests(project: str | Path, timeout: int = 900,
                     gradle_bin: str = "gradle") -> dict:
    p = Path(project)
    exe = gradle_bin
    if (p / "gradlew.bat").is_file():
        exe = str(p / "gradlew.bat")
    elif (p / "gradlew").is_file():
        exe = str(p / "gradlew")
    code, log, ms = _run([exe, "test", "--no-daemon"], p, timeout)
    return _summarize("gradle", p, code, log, ms)


def _summarize(system: str, project: Path, code: int, log: str, ms: int) -> dict:
    total = fails = errs = skipped = 0
    failed_tests: list[str] = []
    for f in glob.glob(str(project / "build" / "test-results" / "test" / "*.xml")):
        try:
            root = ET.parse(f).getroot()
        except ET.ParseError:
            continue
        for suite in ([root] if root.tag == "testsuite" else root.iter("testsuite")):
            total += int(suite.get("tests", 0))
            fails += int(suite.get("failures", 0))
            errs += int(suite.get("errors", 0))
            skipped += int(suite.get("skipped", 0))
            for tc in suite.iter("testcase"):
                if any(True for _ in tc.iter("failure")) or any(True for _ in tc.iter("error")):
                    failed_tests.append(f"{tc.get('classname', '')}.{tc.get('name', '')}")
    ok = code == 0 and fails == 0 and errs == 0 and total > 0
    return {"ok": ok, "system": system, "total": total, "failed": fails,
            "errors": errs, "skipped": skipped,
            "failed_tests": failed_tests[:20],
            "log": log[-8000:], "ms": ms,
            "note": "" if total else "no test results produced"}


def run_pytest(project: str | Path, timeout: int = 600,
               python_bin: str = "") -> dict:
    import sys
    p = Path(project)
    py = python_bin or sys.executable
    code, log, ms = _run([py, "-m", "pytest", "-q"], p, timeout)
    total = fails = 0
    for line in log.splitlines():
        if "passed" in line or "failed" in line:
            import re
            m = re.search(r"(\d+) passed", line)
            f = re.search(r"(\d+) failed", line)
            if m:
                total = max(total, int(m.group(1)))
            if f:
                fails = max(fails, int(f.group(1)))
    total += fails
    ok = code == 0 and fails == 0
    return {"ok": ok, "system": "pytest", "total": total, "failed": fails,
            "errors": 0, "skipped": 0, "failed_tests": [],
            "log": log[-8000:], "ms": ms,
            "note": "" if total else "no test results produced"}
