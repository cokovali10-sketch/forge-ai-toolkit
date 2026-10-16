"""FORGE pipe runner: the conveyor itself.

Runs stages sequentially, each with its own timeout (thread pool, 1 worker).
After every stage a checkpoint is written, so `--resume` skips finished stages.
Headless by design: progress goes to an `on_event` callback, never to a window.

Events: ("stage_start", name) | ("log", text) | ("stage_done", name, status)
        | ("finished", report)
Exit codes for CLI: 0 = all SUCCESS (or allow_fail), 1 = stage FAILED/ERROR,
2 = bad usage.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from forge.core.result import TIMEOUT, ToolResult
from forge.pipe.stages import Stage

Event = tuple
OnEvent = Callable[[Event], None]


@dataclass
class PipeReport:
    target: str
    status: str = "SUCCESS"
    stages: list[dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0
    checkpoint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"target": self.target, "status": self.status,
                "duration_ms": self.duration_ms,
                "stages": self.stages, "checkpoint": self.checkpoint}


def _run_one(fn: Callable[[], ToolResult]) -> ToolResult:
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 - stage crash becomes ERROR result
        return ToolResult(status="ERROR",
                          error={"message": f"{type(e).__name__}: {e}"})


class PipeRunner:
    def __init__(self, stages: list[Stage], ctx: dict[str, Any],
                 checkpoint: str | Path = "", on_event: OnEvent | None = None):
        self.stages = stages
        self.ctx = ctx
        self.checkpoint = Path(checkpoint) if checkpoint else None
        self.on_event = on_event or (lambda e: None)
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def _emit(self, *ev: Any) -> None:
        try:
            self.on_event(tuple(ev))
        except Exception:
            pass

    def _load_done(self) -> dict[str, dict]:
        if self.checkpoint and self.checkpoint.is_file():
            try:
                data = json.loads(self.checkpoint.read_text(encoding="utf-8"))
                return data.get("done", {})
            except (OSError, ValueError):
                return {}
        return {}

    def _save_done(self, done: dict[str, dict]) -> None:
        if self.checkpoint:
            self.checkpoint.write_text(json.dumps({"done": done}, ensure_ascii=False),
                                       encoding="utf-8")

    def run(self, resume: bool = False) -> PipeReport:
        t0 = time.time()
        done = self._load_done() if resume else {}
        report = PipeReport(target=str(self.ctx.get("target", "")),
                            checkpoint=str(self.checkpoint or ""))
        pool = cf.ThreadPoolExecutor(max_workers=1, thread_name_prefix="forge-pipe")
        try:
            for st in self.stages:
                if self._stop:
                    report.status = "CANCELLED"
                    break
                if resume and st.name in done:
                    prev = done[st.name]
                    report.stages.append({"name": st.name, "title": st.title,
                                          **prev, "resumed": True})
                    self._emit("log", f"[{st.name}] пропущено (чекпоинт): {prev.get('status')}")
                    continue
                self._emit("stage_start", st.name)
                t1 = time.time()
                fut = pool.submit(_run_one, lambda s=st: s.fn(self.ctx))
                try:
                    res = fut.result(timeout=st.timeout_s)
                except cf.TimeoutError:
                    res = ToolResult(status=TIMEOUT, error={
                        "message": f"превышен лимит {st.timeout_s}с"},
                        duration_ms=int((time.time() - t1) * 1000))
                entry = {"name": st.name, "title": st.title,
                         **res.envelope()}
                report.stages.append(entry)
                done[st.name] = {"status": res.status,
                                 "duration_ms": res.duration_ms}
                self._save_done(done)
                self._emit("stage_done", st.name, res.status)
                if res.status != "SUCCESS" and not st.allow_fail:
                    report.status = "FAILED"
                    self._emit("log", f"[{st.name}] СТОП: {res.status}")
                    break
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        report.duration_ms = int((time.time() - t0) * 1000)
        self._append_history(report)
        self._emit("finished", report.to_dict())
        return report

    def _append_history(self, report: PipeReport) -> None:
        """Одна строка на прогон: тренды видны без открытия отчётов."""
        try:
            base = Path(str(self.ctx.get("target", "")))
            if not base.is_dir():
                return
            import time as _t
            line = json.dumps(
                {"ts": int(_t.time()), "status": report.status,
                 "duration_ms": report.duration_ms,
                 "stages": [{"name": s["name"], "status": s.get("status"),
                             "duration_ms": s.get("duration_ms", 0)}
                            for s in report.stages]},
                ensure_ascii=False)
            with open(base / ".forge-pipe-history.jsonl", "a",
                      encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass


def exit_code(report: PipeReport) -> int:
    return 0 if report.status == "SUCCESS" else 1
