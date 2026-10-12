"""Workspace sandbox: every file op is confined to an explicit root.

Technical enforcement, not promises: paths are resolved and must stay
inside the workspace, symlinks included. Secrets are never returned.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd|private[_-]?key)\s*[:=]\s*\S+"),
]


class Sandbox:
    DENY_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".gradle"}

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def resolve(self, rel: str) -> Path:
        """Resolve rel inside workspace or raise PermissionError."""
        p = (self.root / rel).resolve()
        if p != self.root and self.root not in p.parents:
            raise PermissionError(f"outside workspace: {rel}")
        return p

    def scrub(self, text: str) -> str:
        for pat in SECRET_PATTERNS:
            text = pat.sub("[REDACTED]", text)
        return text

    def walk(self, rel: str = ".", max_files: int = 2000) -> list[str]:
        base = self.resolve(rel)
        out: list[str] = []
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames
                           if d not in self.DENY_DIRS and not d.startswith(".")]
            for fn in sorted(filenames):
                fp = Path(dirpath) / fn
                try:
                    out.append(str(fp.resolve().relative_to(self.root)))
                except ValueError:
                    continue
                if len(out) >= max_files:
                    return out
        return out

    def search(self, pattern: str, rel: str = ".", max_hits: int = 50) -> list[dict]:
        try:
            rx = re.compile(pattern)
        except re.error as e:
            raise ValueError(f"bad regex: {e}")
        hits: list[dict] = []
        for name in self.walk(rel):
            fp = self.root / name
            try:
                if fp.stat().st_size > 1_000_000:
                    continue
                text = fp.read_text(encoding="utf-8", errors="strict")
            except (OSError, UnicodeError, ValueError):
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    hits.append({"file": name, "line": i,
                                 "text": self.scrub(line.strip()[:300])})
                    if len(hits) >= max_hits:
                        return hits
        return hits

    def read(self, rel: str, limit: int = 4000) -> str:
        fp = self.resolve(rel)
        if not fp.is_file():
            raise FileNotFoundError(rel)
        if fp.stat().st_size > 2_000_000:
            raise ValueError("file too large for read tool")
        return self.scrub(fp.read_text(encoding="utf-8", errors="replace")[:limit])
