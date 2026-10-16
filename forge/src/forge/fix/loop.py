"""Bounded fix mechanism: checkpoint -> check -> bundle -> rollback.

The AGENT writes the fix between cycles; this module guarantees a safe
checkpoint, an honest check result, a visible diff and a one-command
rollback. No silent overwrites, no infinite loops (one cycle per call).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

STATE = ".forge-fix.json"
MAX_BACKUP_MB = 200


def _git(project: Path, *args: str, timeout: int = 60) -> tuple[bool, str]:
    try:
        r = subprocess.run(["git", "-C", str(project), *args],
                           capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _is_repo(project: Path) -> bool:
    ok, _ = _git(project, "rev-parse", "--git-dir")
    return ok


def checkpoint(project: str | Path) -> dict:
    """Save restore point. Returns handle dict (also written to state file)."""
    p = Path(project).resolve()
    handle: dict = {"project": str(p), "at": time.time(), "kind": None}
    if _is_repo(p):
        clean_ok, status = _git(p, "status", "--short")
        ok, sha = _git(p, "rev-parse", "HEAD")
        head = sha.strip() if ok else ""
        if clean_ok and not status.strip():
            # Nothing to stash: record HEAD, rollback restores tracked files.
            handle.update(kind="git-head", head=head)
        else:
            ok, out = _git(p, "stash", "push", "-u", "-m", "forge-fix checkpoint")
            if not ok or "No local changes" in out:
                return {"ok": False, "error": f"stash failed: {out[:300]}"}
            handle.update(kind="git-stash", head=head)
    else:
        try:
            size_mb = sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e6
        except OSError as e:
            return {"ok": False, "error": f"cannot scan project: {e}"}
        if size_mb > MAX_BACKUP_MB:
            return {"ok": False,
                    "error": f"project too large for copy backup ({size_mb:.0f}MB)"}
        backup = Path(str(p) + f".forge-bak-{int(time.time() * 1000)}")
        try:
            shutil.copytree(p, backup, ignore=shutil.ignore_patterns(
                ".git", "__pycache__", ".venv", "node_modules", "build", ".gradle"))
        except OSError as e:
            return {"ok": False, "error": f"backup failed: {e}"}
        handle.update(kind="copy", backup=str(backup))
    handle["ok"] = True
    (p / STATE).write_text(json.dumps(handle, indent=2), encoding="utf-8")
    return handle


def diff(project: str | Path) -> dict:
    p = Path(project).resolve()
    if _is_repo(p):
        ok, out = _git(p, "diff", "--stat")
        ok2, out2 = _git(p, "status", "--short")
        return {"ok": ok, "stat": out[-4000:], "status": out2[-2000:]}
    return {"ok": False, "error": "not a git repo; compare against .forge-bak-* copy"}


def rollback(project: str | Path) -> dict:
    """Restore checkpoint. Refuses if no handle or unknown state."""
    p = Path(project).resolve()
    sf = p / STATE
    if not sf.is_file():
        return {"ok": False, "error": "no checkpoint handle; nothing to roll back"}
    try:
        handle = json.loads(sf.read_text(encoding="utf-8"))
    except Exception as e:
        return {"ok": False, "error": f"broken handle: {e}"}
    if handle.get("kind") == "git-stash":
        ok, out = _git(p, "stash", "pop")
        if ok:
            sf.unlink(missing_ok=True)
        return {"ok": ok, "detail": out[-1000:]}
    if handle.get("kind") == "git-head":
        # Tracked files only: untracked user files are never deleted.
        ok, out = _git(p, "checkout", handle.get("head", "HEAD"), "--", ".")
        if ok:
            sf.unlink(missing_ok=True)
        return {"ok": ok, "detail": out[-1000:] or "tracked files restored"}
    if handle.get("kind") == "copy":
        return {"ok": False,
                "error": f"copy backup at {handle.get('backup')}; restore manually"}
    return {"ok": False, "error": "unknown checkpoint kind"}


def run_check(cmd: list[str], cwd: str | Path, timeout: int = 600) -> dict:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, cwd=str(cwd))
        out = (r.stdout or "") + (r.stderr or "")
        return {"ok": r.returncode == 0, "code": r.returncode,
                "log": out[-8000:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": 124, "log": f"[TIMEOUT {timeout}s]"}
    except FileNotFoundError:
        return {"ok": False, "code": 127, "log": f"missing executable: {cmd[0]}"}


def cycle(project: str | Path, check_cmd: list[str],
          timeout: int = 600) -> dict:
    """One bounded cycle: checkpoint -> check -> failure bundle (no auto-edit)."""
    cp = checkpoint(project)
    if not cp.get("ok"):
        return {"ok": False, "stage": "checkpoint", "detail": cp.get("error", "")}
    res = run_check(check_cmd, project, timeout)
    bundle = {"check": " ".join(check_cmd), "passed": res["ok"],
              "code": res["code"], "log": res["log"][-4000:]}
    if res["ok"]:
        d = diff(project)
        bundle["diff_stat"] = d.get("stat", "")
        return {"ok": True, "stage": "check-passed", "bundle": bundle,
                "hint": "no fix needed; checkpoint kept for rollback"}
    return {"ok": False, "stage": "check-failed", "bundle": bundle,
            "hint": "fix the code, then rerun; rollback available via fix rollback"}
