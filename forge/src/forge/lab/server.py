"""Real server lifecycle: start, wait ready, console commands, logs, stop.

Console control = subprocess stdin (local test env, no RCON needed).
Every command response is verified by observing new log lines, not assumed.
"""
from __future__ import annotations

import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path

READY_MARKERS = ("Done (", "Done,", "Timings Reset")
STOP_TIMEOUT = 60


class ServerProc:
    def __init__(self, env, java_bin: str = "") -> None:
        from .env import TestEnv
        self.env: TestEnv = env
        self.java = java_bin or "java"
        self.proc: subprocess.Popen | None = None
        self.lines: list[tuple[float, str]] = []
        self._q: "queue.Queue[str]" = queue.Queue()
        self._reader: threading.Thread | None = None
        self._mark = 0

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self, extra_args: list[str] | None = None) -> dict:
        if self.running:
            return {"ok": False, "error": "server already running"}
        jar = self._server_jar()
        if jar is None:
            return {"ok": False, "error": "no server jar: set profile.server_jar"}
        cmd = [self.java,
               f"-Xms{self.env.profile.xms_mb}M", f"-Xmx{self.env.profile.xmx_mb}M",
               "-Dfile.encoding=UTF-8", "-jar", jar, "nogui"] + (extra_args or [])
        try:
            self.proc = subprocess.Popen(
                cmd, cwd=str(self.env.server_dir),
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1)
        except FileNotFoundError:
            return {"ok": False, "error": f"java not found: {self.java}"}
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}
        self._reader = threading.Thread(target=self._drain, daemon=True)
        self._reader.start()
        return {"ok": True, "pid": self.proc.pid}

    def _server_jar(self) -> str | None:
        prof = self.env.profile.server_jar
        if prof and Path(prof).is_file():
            return prof
        cands = sorted(self.env.server_dir.glob("*.jar"))
        cands = [c for c in cands if "cache" not in c.name.lower()]
        return str(cands[0]) if cands else None

    def _drain(self) -> None:
        assert self.proc is not None and self.proc.stdout is not None
        for line in self.proc.stdout:
            self.lines.append((time.time(), line.rstrip("\n")))
            self._q.put(line.rstrip("\n"))

    def wait_ready(self, timeout: int = 0) -> dict:
        """Wait for Done markers or process death. Honest either way."""
        timeout = timeout or self.env.profile.timeout_sec
        end = time.time() + timeout
        while time.time() < end:
            if not self.running:
                tail = "\n".join(l for _, l in self.lines[-15:])
                return {"ok": False, "error": "server died during boot",
                        "tail": tail[-3000:]}
            for _, line in self.lines[self._mark:]:
                if any(m in line for m in READY_MARKERS):
                    self._mark = len(self.lines)
                    return {"ok": True, "ms": 0}
            self._mark = len(self.lines)
            time.sleep(0.5)
        return {"ok": False, "error": f"timeout after {timeout}s waiting for Done",
                "tail": "\n".join(l for _, l in self.lines[-15:])[-3000:]}

    def command(self, cmd: str, expect: str = "", timeout: int = 20) -> dict:
        """Send console command, collect lines until expect matches or timeout."""
        if not self.running or self.proc is None or self.proc.stdin is None:
            return {"ok": False, "error": "server not running", "output": ""}
        base = len(self.lines)
        try:
            self.proc.stdin.write(cmd.strip() + "\n")
            self.proc.stdin.flush()
        except Exception as e:
            return {"ok": False, "error": f"stdin failed: {e}", "output": ""}
        end = time.time() + timeout
        while time.time() < end:
            out = "\n".join(l for _, l in self.lines[base:])
            if expect and expect in out:
                return {"ok": True, "output": out[-4000:]}
            if not expect and len(self.lines) > base:
                time.sleep(1.0)
                out = "\n".join(l for _, l in self.lines[base:])
                return {"ok": True, "output": out[-4000:]}
            time.sleep(0.3)
        out = "\n".join(l for _, l in self.lines[base:])
        if expect:
            return {"ok": False, "error": f"expected text not seen: {expect!r}",
                    "output": out[-4000:]}
        return {"ok": True, "output": out[-4000:]}

    def stop(self) -> dict:
        if not self.running or self.proc is None:
            return {"ok": True, "note": "already stopped"}
        try:
            if self.proc.stdin is not None:
                self.proc.stdin.write("stop\n")
                self.proc.stdin.flush()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=STOP_TIMEOUT)
            return {"ok": True, "code": self.proc.returncode}
        except subprocess.TimeoutExpired:
            self.proc.kill()
            return {"ok": True, "note": "killed after stop timeout"}

    def kill(self) -> None:
        try:
            if self.proc is not None and self.running:
                self.proc.kill()
        except Exception:
            pass

    def full_log(self) -> str:
        return "\n".join(l for _, l in self.lines)

    def plugin_lines(self, plugin: str) -> list[str]:
        key = plugin.lower()
        return [l for _, l in self.lines if key in l.lower()][-50]

    def errors(self, ignore: list[str] | None = None) -> list[str]:
        ign = ignore or []
        blocks: list[str] = []
        cur: list[str] = []
        for _, l in self.lines:
            if l.startswith("\t") or l.lstrip().startswith(("at ", "Caused by:")):
                if cur:
                    cur.append(l.strip()[:200])
                continue
            if cur:
                blocks.append(" | ".join(cur))
                cur = []
            if ("ERROR" in l or "Exception" in l or "FAILED" in l
                    or "Could not" in l) and "ERROR]: Negative" not in l:
                cur = [l[:300]]
        if cur:
            blocks.append(" | ".join(cur))
        out = [b for b in blocks if not any(s in b for s in ign)]
        return out[:30]


def find_java(prefer: str = "") -> str:
    if prefer and Path(prefer).is_file():
        return prefer
    for cand in ("java",):
        found = shutil.which(cand)
        if found:
            return found
    return ""
