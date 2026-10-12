"""Test scenarios with PASS/FAIL/ERROR/SKIPPED records and repro steps."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Scenario:
    name: str
    goal: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    # step: {"command": str, "expect": str, "timeout": int}


@dataclass
class ScenarioResult:
    name: str
    status: str  # PASS | FAIL | ERROR | SKIPPED
    goal: str = ""
    expected: str = ""
    actual: str = ""
    repro: list[str] = field(default_factory=list)
    ms: int = 0


def plugin_load(name: str, expect_enabled: str = "") -> Scenario:
    return Scenario(
        name=f"plugin-load:{name}",
        goal=f"Plugin {name} loads and enables without errors",
        steps=[{"command": "plugins",
                "expect": expect_enabled or name, "timeout": 20}],
    )


def log_contains(name: str, text: str) -> Scenario:
    """Asserts text already present in the server log (boot messages)."""
    return Scenario(
        name=f"log-contains:{name}",
        goal=f"Server log contains {text!r}",
        steps=[{"log_contains": text}],
    )


def command_check(command: str, expect: str, timeout: int = 20) -> Scenario:
    return Scenario(
        name=f"command:{command}",
        goal=f"Command /{command} responds as expected",
        steps=[{"command": command, "expect": expect, "timeout": timeout}],
    )


def run(server, scenario: Scenario) -> ScenarioResult:
    t = time.time()
    repro: list[str] = []
    try:
        last: dict = {}
        for step in scenario.steps:
            if "log_contains" in step:
                want = step["log_contains"]
                log = server.full_log() if hasattr(server, "full_log") else ""
                ok = want in log
                repro.append(f"? log contains {want!r}")
                if not ok:
                    return ScenarioResult(
                        scenario.name, "FAIL", scenario.goal,
                        expected=want,
                        actual="not found in server log",
                        repro=repro, ms=int((time.time() - t) * 1000))
                last = {"ok": True, "output": want}
                continue
            last = server.command(step.get("command", ""),
                                  step.get("expect", ""),
                                  step.get("timeout", 20))
            repro.append(f"> {step.get('command', '')}")
            if not last.get("ok"):
                return ScenarioResult(
                    scenario.name, "FAIL", scenario.goal,
                    expected=str(step.get("expect", "")),
                    actual=last.get("output", "")[-1500:] + "\n[" + str(
                        last.get("error", "")) + "]",
                    repro=repro, ms=int((time.time() - t) * 1000))
        return ScenarioResult(
            scenario.name, "PASS", scenario.goal,
            expected="", actual=(last.get("output", "") if scenario.steps else "")[-1500:],
            repro=repro, ms=int((time.time() - t) * 1000))
    except Exception as e:
        return ScenarioResult(scenario.name, "ERROR", scenario.goal,
                              actual=f"{type(e).__name__}: {e}",
                              repro=repro, ms=int((time.time() - t) * 1000))
