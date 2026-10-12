"""FORGE core MVP: module registry + tool protocol.

Backends:
- LocalBackend: in-process python callables (fast, testable).
- AnvilBackend: delegates to an existing Anvil checkout via anvil_call.py,
  so FORGE never duplicates the ~120 Anvil tools. Updates to Anvil/Hermes
  flow through without touching this core.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class ToolDef:
    name: str
    description: str = ""
    version: str = "0.1.0"
    schema: dict = field(default_factory=dict)


@dataclass
class ModuleDef:
    name: str
    description: str = ""
    version: str = "0.1.0"
    tools: list[str] = field(default_factory=list)


class ToolBackend:
    def call(self, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class LocalBackend(ToolBackend):
    def __init__(self) -> None:
        self._tools: dict[str, tuple[ToolDef, Callable[[dict], Any]]] = {}

    def add(self, tool: ToolDef, fn: Callable[[dict], Any]) -> None:
        self._tools[tool.name] = (tool, fn)

    def call(self, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        if tool not in self._tools:
            return {"ok": False, "error": f"unknown tool: {tool}"}
        try:
            res = self._tools[tool][1](params)
            # Functions returning an {"ok": ...} envelope pass through
            # (lets bridges surface backend failures honestly).
            if isinstance(res, dict) and "ok" in res:
                return res
            return {"ok": True, "data": res}
        except Exception as e:  # never leak tracebacks across the protocol
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    def tools(self) -> list[ToolDef]:
        return [t for t, _ in self._tools.values()]

    def schema_of(self, tool: str) -> tuple[dict, str]:
        t, _ = self._tools[tool]
        return t.schema or {"type": "object"}, t.description or tool


class AnvilBackend(ToolBackend):
    """Runs Anvil tools out-of-process. Anvil owns its tools and versions."""

    def __init__(self, anvil_dir: str | Path, timeout: int = 600) -> None:
        self.anvil_dir = Path(anvil_dir)
        self.timeout = timeout

    def schema_of(self, tool: str) -> tuple[dict, str]:
        return ({"type": "object",
                 "properties": {"_params": {"type": "string",
                                            "description": "tool params as JSON"}}},
                f"Anvil tool {tool} (params vary per tool)")

    def call(self, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        script = self.anvil_dir / "anvil_call.py"
        if not script.is_file():
            return {"ok": False, "error": f"anvil_call.py not found in {self.anvil_dir}"}
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(params, f)
            param_file = f.name
        try:
            out = subprocess.run(
                [sys.executable, str(script), tool, param_file],
                capture_output=True, text=True, timeout=self.timeout,
                cwd=str(self.anvil_dir),
            )
            try:
                return json.loads(out.stdout or "{}")
            except json.JSONDecodeError:
                return {"ok": False, "error": (out.stderr or out.stdout)[:500]}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"anvil tool timed out: {tool}"}
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}


class Registry:
    """Modules + tools index. Versioned: registry reports backend versions."""

    def __init__(self) -> None:
        self.modules: dict[str, ModuleDef] = {}
        self.backends: dict[str, ToolBackend] = {}
        self.tool_owner: dict[str, str] = {}

    def add_backend(self, name: str, backend: ToolBackend) -> None:
        self.backends[name] = backend

    def add_module(self, module: ModuleDef, backend: str = "local") -> None:
        self.modules[module.name] = module
        for t in module.tools:
            self.tool_owner.setdefault(t, backend)

    def list_modules(self) -> list[ModuleDef]:
        return sorted(self.modules.values(), key=lambda m: m.name)

    def call(self, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        owner = self.tool_owner.get(tool)
        if owner is None or owner not in self.backends:
            return {"ok": False, "error": f"unknown tool: {tool}"}
        return self.backends[owner].call(tool, params)
