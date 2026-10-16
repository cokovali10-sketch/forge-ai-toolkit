"""FORGE pipe watch: перезапуск конвейера при изменении файлов.

Чистый stdlib (поток + mtime-снапшоты, без watchdog-зависимости).
Headless-safe: никакого GUI здесь нет, только колбэк on_change.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__",
             "build", "target", "out", ".gradle", ".idea", "dist",
             "lab-servers"}
# собственные артефакты конвейера не должны его перезапускать
SKIP_FILES = {"forge-pipe-checkpoint.json", "forge-pipe-report.json",
              ".forge-pipe-history.jsonl"}
WATCH_EXTS = {".py", ".java", ".js", ".ts", ".tsx", ".kt", ".go", ".rs",
              ".yml", ".yaml", ".toml", ".json", ".xml", ".gradle"}


def snapshot(root: str | Path) -> dict[str, float]:
    base = Path(root)
    out: dict[str, float] = {}
    if not base.is_dir():
        return out
    n = 0
    for dirpath, dirnames, filenames in __import__("os").walk(base, onerror=lambda e: None):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn in SKIP_FILES:
                continue
            if Path(fn).suffix.lower() not in WATCH_EXTS:
                continue
            n += 1
            if n > 30000:
                dirnames[:] = []
                break
            fp = Path(dirpath) / fn
            try:
                out[str(fp.relative_to(base))] = fp.stat().st_mtime
            except OSError:
                pass
        if n > 30000:
            break
    return out


def changed(old: dict[str, float], new: dict[str, float]) -> list[str]:
    keys = set(old) | set(new)
    return sorted(k for k in keys if old.get(k) != new.get(k))


class Watcher:
    """Фоновый наблюдатель. on_change(changed_files) вызывается с дебаунсом."""

    def __init__(self, root: str, on_change, interval_s: float = 2.0,
                 debounce_s: float = 1.5):
        self.root = root
        self.on_change = on_change
        self.interval_s = interval_s
        self.debounce_s = debounce_s
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="forge-pipe-watch")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive() and not self._stop.is_set())

    def _loop(self) -> None:
        prev = snapshot(self.root)
        pending: list[str] = []
        last_fire = 0.0
        while not self._stop.is_set():
            time.sleep(self.interval_s)
            if self._stop.is_set():
                break
            cur = snapshot(self.root)
            diff = changed(prev, cur)
            prev = cur
            if diff:
                pending = sorted(set(pending) | set(diff))
                last_fire = time.time()
            if pending and time.time() - last_fire >= self.debounce_s:
                fire, pending = pending, []
                try:
                    self.on_change(fire)
                except Exception:
                    pass
