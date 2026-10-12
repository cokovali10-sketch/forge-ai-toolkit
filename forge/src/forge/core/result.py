"""Standard ToolResult (master spec, part V), backward compatible.

New envelope: status/result/error/warnings/duration_ms/artifacts/provenance.
Legacy keys ok/data are ALWAYS present so old callers keep working.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

SUCCESS = "SUCCESS"
FAILED = "FAILED"
ERROR = "ERROR"
TIMEOUT = "TIMEOUT"
CANCELLED = "CANCELLED"
DENIED = "DENIED"
NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


@dataclass
class ToolResult:
    status: str = SUCCESS
    result: Any = None
    error: dict | None = None
    warnings: list[str] = field(default_factory=list)
    duration_ms: int = 0
    artifacts: list[dict] = field(default_factory=list)
    provenance: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == SUCCESS

    def envelope(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "ok": self.ok,
            "status": self.status,
            "duration_ms": self.duration_ms,
        }
        if self.ok:
            out["data"] = self.result
            out["result"] = self.result
        else:
            out["error"] = self.error or {"message": self.status}
        if self.warnings:
            out["warnings"] = self.warnings
        if self.artifacts:
            out["artifacts"] = self.artifacts
        if self.provenance:
            out["provenance"] = self.provenance
        return out


def timed(fn, *args, **kwargs) -> ToolResult:
    t = time.time()
    try:
        return ToolResult(status=SUCCESS, result=fn(*args, **kwargs),
                          duration_ms=int((time.time() - t) * 1000))
    except TimeoutError:
        return ToolResult(status=TIMEOUT,
                          error={"message": "timeout"},
                          duration_ms=int((time.time() - t) * 1000))
    except PermissionError as e:
        return ToolResult(status=DENIED, error={"message": str(e)},
                          duration_ms=int((time.time() - t) * 1000))
    except NotImplementedError as e:
        return ToolResult(status=NOT_IMPLEMENTED,
                          error={"message": str(e) or "not implemented"},
                          duration_ms=int((time.time() - t) * 1000))
    except Exception as e:
        return ToolResult(status=ERROR,
                          error={"message": f"{type(e).__name__}: {e}"},
                          duration_ms=int((time.time() - t) * 1000))
