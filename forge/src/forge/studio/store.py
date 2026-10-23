"""Studio project registry: a small, atomic JSON file, no database.

Only explicitly added directories are visible to the Studio API. Paths are
resolved once and compared case-insensitively on Windows.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

FORGE_ROOT = Path(__file__).resolve().parents[3]      # .../forge
REPO_ROOT = FORGE_ROOT.parent                         # .../Forge-Factority
DEFAULT_STORE = REPO_ROOT / ".forge-studio.json"


class Store:
    def __init__(self, path: str | Path = DEFAULT_STORE) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    def _read(self) -> dict:
        if not self.path.is_file():
            return {"projects": [], "selected": ""}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"projects": [], "selected": ""}
        if not isinstance(data, dict):
            return {"projects": [], "selected": ""}
        data.setdefault("projects", [])
        data.setdefault("selected", "")
        return data

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        os.replace(tmp, self.path)

    @staticmethod
    def _key(path: str | Path) -> str:
        return os.path.normcase(str(Path(path).resolve()))

    def load(self) -> dict:
        with self._lock:
            return self._read()

    def list(self) -> list[dict]:
        return list(self.load().get("projects", []))

    def get(self, path: str | Path) -> dict | None:
        key = self._key(path)
        return next((p for p in self.list() if self._key(p["path"]) == key),
                    None)

    def selected(self) -> dict | None:
        data = self.load()
        sel = data.get("selected")
        if not sel:
            return None
        return self.get(sel) or (data["projects"][0]
                                 if data.get("projects") else None)

    def add(self, path: str | Path, name: str = "") -> dict:
        p = Path(path).resolve()
        if not p.is_dir():
            raise ValueError(f"not a directory: {p}")
        with self._lock:
            data = self._read()
            key = self._key(p)
            for item in data["projects"]:
                if self._key(item["path"]) == key:
                    if name:
                        item["name"] = name
                    data["selected"] = str(p)
                    self._write(data)
                    return item
            if len(data["projects"]) >= 50:
                raise ValueError("project limit reached (50)")
            item = {"path": str(p), "name": name or p.name,
                    "added_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "score": None, "verdict": "", "last_report_at": ""}
            data["projects"].append(item)
            data["selected"] = str(p)
            self._write(data)
            return item

    def remove(self, path: str | Path) -> bool:
        key = self._key(path)
        with self._lock:
            data = self._read()
            before = len(data["projects"])
            data["projects"] = [p for p in data["projects"]
                                if self._key(p["path"]) != key]
            if data.get("selected") and self._key(data["selected"]) == key:
                data["selected"] = (data["projects"][0]["path"]
                                    if data["projects"] else "")
            self._write(data)
            return len(data["projects"]) != before

    def select(self, path: str | Path) -> dict | None:
        item = self.get(path)
        if item is None:
            return None
        with self._lock:
            data = self._read()
            data["selected"] = item["path"]
            self._write(data)
        return item

    def remember_report(self, path: str | Path, score, verdict: str) -> None:
        key = self._key(path)
        with self._lock:
            data = self._read()
            for item in data["projects"]:
                if self._key(item["path"]) == key:
                    item["score"] = score
                    item["verdict"] = verdict
                    item["last_report_at"] = time.strftime(
                        "%Y-%m-%d %H:%M:%S")
                    break
            else:
                return
            self._write(data)
