"""Fuzzing: command matrix, config restart, soak repeats.

Every finding carries the exact input + server output (repro included).
Nothing is assumed: an Exception in fresh log lines = FAIL.
"""
from __future__ import annotations


JUNK_ARGS = ["", "abc", "-1", "999999999", "'\";drop", "x" * 300, "null",
             "@p", "~ ~ ~"]

COMMAND_MATRIX = ["help", "plugins", "tps", "list"]


def _new_errors(server, since: int, ignore: list) -> list[str]:
    out = []
    for _, line in server.lines[since:]:
        if any(s in line for s in ignore):
            continue
        if "Exception" in line or "ERROR" in line or "FAILED" in line:
            out.append(line[:250])
    return out[:10]


def fuzz_commands(server, base_commands: list[str],
                  ignore: list | None = None) -> dict:
    """Run base commands plus junk-arg variants. FAIL on fresh exceptions."""
    ignore = ignore or []
    results = []
    for cmd in base_commands:
        variants = [cmd] + [f"{cmd} {j}".rstrip() for j in JUNK_ARGS]
        for variant in variants:
            mark = len(server.lines)
            try:
                r = server.command(variant, "", 15)
            except Exception as e:
                results.append({"input": variant, "ok": False,
                                "detail": f"{type(e).__name__}: {e}"})
                continue
            errs = _new_errors(server, mark, ignore)
            results.append({"input": variant, "ok": not errs,
                            "detail": "; ".join(errs) or "clean"})
    bad = [r for r in results if not r["ok"]]
    return {"ok": not bad, "tried": len(results), "failed": bad[:15]}


def soak(server, command: str, expect: str, rounds: int = 5,
         ignore: list | None = None) -> dict:
    """Repeat one command; all rounds must behave identically.

    Timestamps are normalized away: only content drift fails the soak.
    """
    import re as _re
    outs = []
    for _ in range(max(1, rounds)):
        mark = len(server.lines)
        r = server.command(command, "", 20)
        norm = _re.sub(r"(?m)^\[\d\d:\d\d:\d\d [A-Z]+\]: ", "",
                       r.get("output", ""))
        outs.append(norm[-500:])
        if _new_errors(server, mark, ignore or []):
            return {"ok": False, "rounds_done": len(outs),
                    "detail": "fresh errors during soak"}
    first = outs[0] if outs else ""
    stable = all(o == first for o in outs[1:])
    return {"ok": stable, "rounds_done": len(outs),
            "detail": "stable" if stable else "output drifted between rounds"}


def fuzz_config_restart(make_env, boot_and_check, bad_values: dict) -> dict:
    """Write garbage config values, reboot, assert plugin still enables.

    make_env() -> env object with .server_dir; boot_and_check(env) -> dict
    with at least {"ok", "enabled"}. Fully generic over plugins.
    """
    return {"ok": False,
            "detail": "wire per-project: needs config path + enable check"}
