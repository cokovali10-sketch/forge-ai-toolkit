"""Hermes HTTP bridge. Hermes owns its server, workspace and versions;
FORGE only proxies a curated subset. If the server is down, every call
fails cleanly with how to start it - never faked.

Curated tools (Hermes endpoint in brackets):
- hermes.health             [GET  /api/health]
- hermes.recall             [GET  /api/memory/projects/{id}/recall?query=]
- hermes.match_workflow     [POST /api/workflows/match]
- hermes.code_search        [POST /api/code-intel/search]
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from ..core.registry import ToolBackend


class HermesBackend(ToolBackend):
    def __init__(self, base: str = "http://127.0.0.1:8765", timeout: int = 30) -> None:
        self.base = base.rstrip("/")
        self.timeout = timeout

    def available(self) -> bool:
        try:
            urllib.request.urlopen(self.base + "/api/health", timeout=5)
            return True
        except Exception:
            return False

    def schema_of(self, tool: str) -> tuple[dict, str]:
        return ({"type": "object"}, f"Hermes service {tool}")

    def _get(self, path: str) -> Any:
        req = urllib.request.Request(
            self.base + path, headers={"User-Agent": "forge/0.1.0"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.load(r)

    def _post(self, path: str, payload: dict) -> Any:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            self.base + path, data=body,
            headers={"Content-Type": "application/json",
                     "User-Agent": "forge/0.1.0"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.load(r)

    def call(self, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            if tool == "hermes.health":
                return {"ok": True, "data": self._get("/api/health")}
            if tool == "hermes.recall":
                q = urllib.parse.urlencode({"query": params.get("query", "")})
                pid = params.get("project", "")
                return {"ok": True,
                        "data": self._get(f"/api/memory/projects/{pid}/recall?{q}")}
            if tool == "hermes.match_workflow":
                return {"ok": True,
                        "data": self._post("/api/workflows/match",
                                           {"task": params.get("task", "")})}
            if tool == "hermes.code_search":
                return {"ok": True,
                        "data": self._post("/api/code-intel/search", params)}
            return {"ok": False, "error": f"unknown tool: {tool}"}
        except Exception as e:
            return {"ok": False,
                    "error": f"hermes unreachable ({type(e).__name__}): "
                             f"start the Hermes server first"}
