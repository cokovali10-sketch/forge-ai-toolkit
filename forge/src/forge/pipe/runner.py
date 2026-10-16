"""FORGE pipe runner: the conveyor itself.

Fast stages run IN PARALLEL (all read-only); heavy ones strictly after,
and only if fast are green. Each stage keeps its own timeout.
After every stage a checkpoint is written, so `--resume` skips finished
stages and fingerprints skip unchanged ones.
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

    def _fingerprint(self, st: Stage) -> str | None:
        if not st.fingerprint:
            return None
        try:
            return st.fingerprint(self.ctx)
        except Exception:
            return None

    def _cached_entry(self, st: Stage, prev: dict) -> dict | None:
        """Перезапуск только затронутого: входы не изменились — берём из чекпоинта."""
        if "envelope" not in prev:
            return None  # старый формат чекпоинта — пересчитать честно
        fp = self._fingerprint(st)
        if fp is None or prev.get("fingerprint") != fp:
            return None
        entry = {"name": st.name, "title": st.title, "cached": True}
        entry.update(prev["envelope"])
        return entry

    def _store(self, st: Stage, res: ToolResult,
               done: dict[str, dict]) -> dict[str, Any]:
        entry = {"name": st.name, "title": st.title, **res.envelope()}
        fp = self._fingerprint(st)
        saved: dict[str, Any] = {"status": res.status,
                                 "duration_ms": res.duration_ms,
                                 "envelope": res.envelope()}
        if fp is not None:
            saved["fingerprint"] = fp
        done[st.name] = saved
        self._save_done(done)
        self._emit("stage_done", st.name, res.status)
        return entry

    def _timed_out(self, st: Stage, t1: float) -> ToolResult:
        return ToolResult(status=TIMEOUT, error={
            "message": f"превышен лимит {st.timeout_s}с"},
            duration_ms=int((time.time() - t1) * 1000))

    def _run_sequential(self, todo: list[Stage], done: dict[str, dict],
                        results: dict[str, dict]) -> bool:
        """Строго по очереди, стоп на первой несогласованной. Возвращает failed."""
        failed = False
        for st in todo:
            if self._stop:
                return True
            self._emit("stage_start", st.name)
            t1 = time.time()
            with cf.ThreadPoolExecutor(max_workers=1,
                                       thread_name_prefix="forge-pipe") as pool:
                fut = pool.submit(_run_one, lambda s=st: s.fn(self.ctx))
                try:
                    res = fut.result(timeout=st.timeout_s)
                except cf.TimeoutError:
                    res = self._timed_out(st, t1)
            results[st.name] = self._store(st, res, done)
            if res.status != "SUCCESS" and not st.allow_fail:
                self._emit("log", f"[{st.name}] СТОП: {res.status}")
                return True
        return failed

    def _run_batch(self, todo: list[Stage], done: dict[str, dict],
                   results: dict[str, dict]) -> bool:
        """Параллельно: все быстрые стадии сразу, итог — по худшему.

        Таймаут каждой стадии считается от её старта (дедлайн), а не от
        момента опроса — иначе as_completed съедал бы таймауты.
        """
        futs: dict[Any, tuple[Stage, float]] = {}
        pool = cf.ThreadPoolExecutor(max_workers=max(1, len(todo)),
                                     thread_name_prefix="forge-pipe")
        try:
            for st in todo:
                self._emit("stage_start", st.name)
                futs[pool.submit(_run_one, lambda s=st: s.fn(self.ctx))] = (st, time.time())
            for fut, (st, t1) in futs.items():
                if self._stop:
                    for f in futs:
                        f.cancel()
                    results[st.name] = {"name": st.name, "title": st.title,
                                        "ok": False, "status": "CANCELLED",
                                        "duration_ms": 0}
                    return True
                try:
                    res = fut.result(timeout=max(0.0, t1 + st.timeout_s - time.time()))
                except cf.TimeoutError:
                    res = self._timed_out(st, t1)
                results[st.name] = self._store(st, res, done)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        return False

    def run(self, resume: bool = False, serial: bool = False) -> PipeReport:
        t0 = time.time()
        done = self._load_done()  # нужен всегда: resume + fingerprint-кэш
        report = PipeReport(target=str(self.ctx.get("target", "")),
                            checkpoint=str(self.checkpoint or ""))
        # Фаза 1: resume/кэш — дёшево и последовательно
        pre: dict[str, dict] = {}
        pending: list[Stage] = []
        for st in self.stages:
            if self._stop:
                report.status = "CANCELLED"
                return self._finish(report, t0)
            prev = done.get(st.name, {})
            if resume and st.name in done:
                base = prev.get("envelope", {"status": prev.get("status"),
                                             "duration_ms": prev.get("duration_ms", 0)})
                pre[st.name] = {"name": st.name, "title": st.title,
                                **base, "resumed": True}
                self._emit("log", f"[{st.name}] пропущено (чекпоинт): {base.get('status')}")
                continue
            hit = self._cached_entry(st, prev) if not resume else None
            if hit:
                pre[st.name] = hit
                self._emit("log", f"[{st.name}] кэш: входы не изменились")
                continue
            pending.append(st)
        # Фаза 2: быстрые — пачкой (или очередью при --serial), тяжёлые — строго после
        results: dict[str, dict] = {}
        fast = [s for s in pending if not s.heavy]
        heavy = [s for s in pending if s.heavy]
        failed = False
        if fast:
            if serial:
                failed = self._run_sequential(fast, done, results)
            else:
                failed = self._run_batch(fast, done, results)
                failed = failed or any(
                    results[s.name].get("status") != "SUCCESS" and not s.allow_fail
                    for s in fast if s.name in results)
        if self._stop:
            report.status = "CANCELLED"
        elif heavy and failed:
            for st in heavy:  # дорогие не гоняем на красном фундаменте
                results[st.name] = {"name": st.name, "title": st.title,
                                    "ok": False, "status": "SKIPPED",
                                    "duration_ms": 0,
                                    "skipped_reason": "fast stages failed"}
                self._emit("log", f"[{st.name}] пропущена: быстрые упали")
            report.status = "FAILED"
        elif heavy:
            if self._stop:
                report.status = "CANCELLED"
            elif self._run_sequential(heavy, done, results):
                report.status = "FAILED"
        if report.status != "CANCELLED":
            bad = [s for s in pending
                   if s.name in results
                   and results[s.name].get("status") != "SUCCESS"
                   and not s.allow_fail]
            if bad:
                report.status = "FAILED"
        for st in self.stages:  # порядок отчёта = порядок объявления
            if st.name in pre:
                report.stages.append(pre[st.name])
            elif st.name in results:
                report.stages.append(results[st.name])
        if report.status != "CANCELLED":
            # статус учитывает ВСЕ записи, включая кэш: старый FAIL — это FAIL
            allowed = {s.name: s.allow_fail for s in self.stages}
            if any(s.get("status") != "SUCCESS" and not allowed.get(s.get("name"), False)
                   for s in report.stages):
                report.status = "FAILED"
        return self._finish(report, t0)

    def _finish(self, report: PipeReport, t0: float) -> PipeReport:
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
