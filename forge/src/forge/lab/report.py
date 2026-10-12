"""Run reports: config, versions, timings, results, artifacts. Markdown out."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RunReport:
    run_id: str
    checks: list[dict[str, Any]] = field(default_factory=list)
    started: float = field(default_factory=time.time)

    def add(self, stage: str, ok: bool, detail: str = "", ms: int = 0) -> None:
        self.checks.append({"stage": stage, "ok": ok, "detail": detail[:2000], "ms": ms})

    def passed(self) -> bool:
        return all(c["ok"] for c in self.checks)

    def markdown(self) -> str:
        lines = [f"# FORGE Testing Lab run {self.run_id}", ""]
        for c in self.checks:
            mark = "PASS" if c["ok"] else "FAIL"
            lines.append(f"- [{mark}] {c['stage']} ({c['ms']}ms)")
            if c["detail"]:
                lines.append(f"  {c['detail'][:1500]}")
        lines += ["", f"Result: {'PASS' if self.passed() else 'FAIL'}"]
        return "\n".join(lines)

    def save(self, artifacts_dir: str | Path) -> str:
        p = Path(artifacts_dir) / "report.md"
        p.write_text(self.markdown(), encoding="utf-8")
        return str(p)
