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
    level: int = 1  # 0 read, 1 local-reversible, 2 execute, 3 external, 4 sensitive
    timeout: int = 300
    confirm: bool = False


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
            from .result import ToolResult, ERROR
            return ToolResult(status=ERROR,
                              error={"message": f"unknown tool: {tool}"}).envelope()
        from .result import timed
        import concurrent.futures as _fut
        tdef, fn = self._tools[tool]
        try:
            with _fut.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(fn, params)
                res = fut.result(timeout=tdef.timeout)
        except _fut.TimeoutError:
            from .result import ToolResult, TIMEOUT
            return ToolResult(status=TIMEOUT, error={
                "message": f"timeout after {tdef.timeout}s"}).envelope()
        except Exception as e:
            from .result import ToolResult, ERROR
            return ToolResult(status=ERROR, error={
                "message": f"{type(e).__name__}: {e}"}).envelope()
        if isinstance(res, dict) and "ok" in res:
            return res
        return timed(lambda: res).envelope()

    def tools(self) -> list[ToolDef]:
        return [t for t, _ in self._tools.values()]

    def schema_of(self, tool: str) -> tuple[dict, str]:
        t, _ = self._tools[tool]
        return t.schema or {"type": "object"}, t.description or tool

    def level_of(self, tool: str) -> int | None:
        entry = self._tools.get(tool)
        return entry[0].level if entry else None


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
        self.tool_module: dict[str, str] = {}
        self.disabled: set[str] = set()

    def disable(self, module: str) -> bool:
        if module not in self.modules:
            return False
        self.disabled.add(module)
        return True

    def enable(self, module: str) -> bool:
        if module not in self.modules:
            return False
        self.disabled.discard(module)
        return True

    def is_enabled(self, module: str) -> bool:
        return module in self.modules and module not in self.disabled

    def status_of(self, module: str) -> str:
        if module not in self.modules:
            return "FAILED"
        return "DISABLED" if module in self.disabled else "ENABLED"

    def add_backend(self, name: str, backend: ToolBackend) -> None:
        self.backends[name] = backend

    def add_module(self, module: ModuleDef, backend: str = "local") -> None:
        self.modules[module.name] = module
        for t in module.tools:
            self.tool_owner.setdefault(t, backend)
            self.tool_module.setdefault(t, module.name)

    def list_modules(self) -> list[ModuleDef]:
        return sorted(self.modules.values(), key=lambda m: m.name)

    def level_of(self, tool: str) -> int | None:
        """Permission level or None when the tool is unknown."""
        for back in self.backends.values():
            get = getattr(back, "level_of", None)
            if callable(get):
                try:
                    lvl = get(tool)
                except Exception:
                    lvl = None
                if lvl is not None:
                    return lvl
        if tool.startswith("hermes."):
            return 1
        return None

    def call(self, tool: str, params: dict[str, Any],
             allow_level: int = 2) -> dict[str, Any]:
        from .result import ToolResult, DENIED, ERROR
        owner = self.tool_owner.get(tool)
        if owner is None or owner not in self.backends:
            return ToolResult(status=ERROR, error={
                "message": f"unknown tool: {tool}"}).envelope()
        mod = self.tool_module.get(tool)
        if mod is not None and not self.is_enabled(mod):
            return ToolResult(status=DENIED, error={
                "message": f"module disabled: {mod}"}).envelope()
        lvl = self.level_of(tool)
        if lvl is None:
            lvl = 2
        if lvl > allow_level:
            return ToolResult(status=DENIED, error={
                "message": f"tool {tool} needs level {lvl} "
                           f"(allowed {allow_level})"}).envelope()
        return self.backends[owner].call(tool, params)
