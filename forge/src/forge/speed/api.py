"""Speed department API: batch writes/patches, context packs, blueprints.

These functions exist to cut agent round-trips. One call can create dozens of
files, apply dozens of edits, or return the exact slice of a repository the
model needs next — instead of one tool call per file.
"""
from __future__ import annotations

import base64
import difflib
import math
import re
import shutil
import statistics
import time
from pathlib import Path
from typing import Any

from . import recipes as _recipes
from .files import (MAX_BYTES, MAX_FILES, LANG, apply_batch, read_text,
                    resolve, resolve_cached, tree_text, validate_root,
                    walk_files)

_SECRET = re.compile(
    r"(?i)(api[_-]?key|token|secret|password|passwd|private[_-]?key)"
    r"\s*[:=]\s*\S+")


def _scrub(text: str) -> str:
    return _SECRET.sub("[REDACTED]", text)


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _file_items(files: Any) -> list[dict]:
    if isinstance(files, dict):
        return [{"path": k, "content": v} for k, v in files.items()]
    if isinstance(files, list):
        out = []
        for item in files:
            if not isinstance(item, dict):
                raise ValueError("each file must be an object with path/content")
            out.append(item)
        return out
    raise ValueError("files must be an object {path: content} or a list")


# --------------------------------------------------------------------------
# speed.write — many files in one atomic transaction
# --------------------------------------------------------------------------

def write(root: str, files: Any, atomic: bool = True,
          backup: bool = False, dry_run: bool = False) -> dict[str, Any]:
    t0 = time.perf_counter()
    base = validate_root(root, create=True)
    items = _file_items(files)
    if not items:
        return {"ok": False, "error": "files is empty", "duration_ms": _ms(t0)}
    if len(items) > MAX_FILES:
        return {"ok": False, "error": f"too many files: {len(items)}"}
    staged: dict[str, bytes | None] = {}
    planned: list[dict] = []
    errors: list[dict] = []
    total = 0
    cache: dict[str, Path] = {}
    for item in items:
        rel = str(item.get("path") or item.get("file") or "").strip()
        try:
            if not rel:
                raise ValueError("empty path")
            target = resolve_cached(base, rel, cache)
            if target.is_dir():
                raise IsADirectoryError(rel)
            mode = str(item.get("mode", "write")).lower()
            if mode not in ("write", "create", "append"):
                raise ValueError(f"bad mode: {mode}")
            if mode == "create" and target.exists():
                errors.append({"path": rel, "error": "already exists"})
                continue
            if "base64" in item:
                try:
                    data = base64.b64decode(str(item["base64"]), validate=True)
                except Exception as e:
                    raise ValueError(f"bad base64: {e}") from e
            else:
                encoding = str(item.get("encoding", "utf-8"))
                data = str(item.get("content", item.get("text", ""))).encode(
                    encoding)
            if mode == "append":
                prior = staged.get(rel)
                if prior is None and target.is_file():
                    prior = target.read_bytes()
                data = (prior or b"") + data
            if rel in staged and mode != "append":
                raise ValueError("duplicate path in batch")
            staged[rel] = data
            total += len(data)
            planned.append({"path": rel, "bytes": len(data), "mode": mode})
        except (ValueError, OSError, PermissionError) as e:
            errors.append({"path": rel, "error": f"{type(e).__name__}: {e}"})
    if errors:
        return {"ok": False, "root": str(base), "errors": errors,
                "written": [], "duration_ms": _ms(t0)}
    if total > MAX_BYTES:
        return {"ok": False, "error": f"batch too large: {total} bytes"}
    if dry_run:
        return {"ok": True, "root": str(base), "dry_run": True,
                "would_write": planned, "files": len(planned),
                "bytes": total, "duration_ms": _ms(t0)}
    try:
        res = apply_batch(base, staged, backup=backup, atomic=atomic)
    except (OSError, ValueError, PermissionError) as e:
        return {"ok": False, "root": str(base), "error": f"{type(e).__name__}: {e}",
                "duration_ms": _ms(t0)}
    return {"ok": True, "root": str(base), "files": len(res["written"]),
            "bytes": res["bytes"], "written": res["written"],
            "backup": res.get("backup", ""), "atomic": res.get("atomic", atomic),
            "duration_ms": _ms(t0)}


# --------------------------------------------------------------------------
# speed.patch — many exact/regex edits in one transaction
# --------------------------------------------------------------------------

def _compile(find: str, regex: bool, flags: str) -> re.Pattern | None:
    if not regex:
        return None
    bits = 0
    if "i" in flags:
        bits |= re.IGNORECASE
    if "m" in flags:
        bits |= re.MULTILINE
    if "s" in flags:
        bits |= re.DOTALL
    try:
        return re.compile(find, bits)
    except re.error as e:
        raise ValueError(f"bad regex {find!r}: {e}") from e


def _count(text: str, find: str, rx: re.Pattern | None) -> int:
    return len(rx.findall(text)) if rx else text.count(find)


def patch(root: str, edits: list[dict], dry_run: bool = False,
          backup: bool = False, diff: bool = True,
          atomic: bool = True) -> dict[str, Any]:
    t0 = time.perf_counter()
    base = validate_root(root)
    if not isinstance(edits, list) or not edits:
        return {"ok": False, "error": "edits must be a non-empty list"}
    if len(edits) > MAX_FILES * 4:
        return {"ok": False, "error": f"too many edits: {len(edits)}"}
    stage: dict[str, str] = {}
    originals: dict[str, str] = {}
    details: list[dict] = []
    errors: list[dict] = []
    per_file: dict[str, str] = {}
    cache: dict[str, Path] = {}
    for n, edit in enumerate(edits):
        if not isinstance(edit, dict):
            errors.append({"edit": n, "error": "edit must be an object"})
            continue
        rel = str(edit.get("path") or edit.get("file") or "").strip()
        find = str(edit.get("find", ""))
        repl = str(edit.get("replace", ""))
        regex = bool(edit.get("regex", False))
        all_ = bool(edit.get("all", False))
        flags = str(edit.get("flags", ""))
        try:
            if not rel:
                raise ValueError("path is required")
            if not find:
                raise ValueError("find is required")
            target = resolve_cached(base, rel, cache)
            if any(part == ".git" for part in target.relative_to(base).parts):
                raise PermissionError("refusing to patch .git")
            if rel not in per_file:
                if not target.is_file():
                    raise FileNotFoundError(rel)
                originals[rel] = read_text(target)
                per_file[rel] = originals[rel]
            text = per_file[rel]
            rx = _compile(find, regex, flags)
            count = _count(text, find, rx)
            expected = edit.get("expected")
            if expected is not None and int(expected) != count:
                raise ValueError(f"expected {expected} matches, found {count}")
            if count == 0 and expected is None:
                raise ValueError("find text not found")
            if not all_ and count > 1:
                raise ValueError(f"find is ambiguous ({count} matches); "
                                 "set all=true")
            if regex:
                new = rx.sub(repl, text, count=0 if all_ else 1)  # type: ignore[union-attr]
            else:
                new = text.replace(find, repl, -1 if all_ else 1)
            per_file[rel] = new
            details.append({"path": rel, "matches": count,
                            "replaced": count if all_ else min(count, 1),
                            "regex": regex})
        except (ValueError, OSError, PermissionError) as e:
            errors.append({"edit": n, "path": rel, "error": f"{type(e).__name__}: {e}"})
    if errors:
        return {"ok": False, "root": str(base), "errors": errors,
                "edited": [], "duration_ms": _ms(t0)}
    for rel, new in per_file.items():
        if new != originals[rel]:
            stage[rel] = new
    if not stage:
        return {"ok": True, "root": str(base), "edited": [], "dry_run": dry_run,
                "details": details, "duration_ms": _ms(t0)}
    diffs = []
    if diff:
        for rel, new in stage.items():
            d = list(difflib.unified_diff(
                originals[rel].splitlines(), new.splitlines(),
                fromfile=rel, tofile=rel, lineterm="", n=2))
            diffs.append({"path": rel, "diff": "\n".join(d[:160])})
    if dry_run:
        return {"ok": True, "root": str(base), "dry_run": True, "edited": [],
                "would_edit": [{"path": p, "old_chars": len(originals[p]),
                                "new_chars": len(stage[p])} for p in stage],
                "details": details, "diffs": diffs, "duration_ms": _ms(t0)}
    try:
        res = apply_batch(base, {k: v.encode("utf-8") for k, v in stage.items()},
                          backup=backup, atomic=atomic)
    except (OSError, ValueError, PermissionError) as e:
        return {"ok": False, "root": str(base), "error": f"{type(e).__name__}: {e}",
                "duration_ms": _ms(t0)}
    return {"ok": True, "root": str(base), "edited": res["written"],
            "files": len(stage), "details": details, "diffs": diffs,
            "backup": res.get("backup", ""), "duration_ms": _ms(t0)}


# --------------------------------------------------------------------------
# speed.search — all patterns in one file pass
# --------------------------------------------------------------------------

def _scan(base: Path, patterns: list[str], sub: str = ".",
          globs: list[str] | None = None, max_hits: int = 200,
          context: int = 0, ignore_case: bool = False,
          regex: bool = True, max_file_bytes: int = 1_000_000,
          include_hidden: bool = False) -> dict[str, Any]:
    t0 = time.perf_counter()
    if not patterns:
        raise ValueError("at least one pattern is required")
    bits = re.IGNORECASE if ignore_case else 0
    compiled: list[tuple[str, re.Pattern | None]] = []
    for p in patterns:
        if regex:
            try:
                compiled.append((p, re.compile(p, bits)))
            except re.error as e:
                raise ValueError(f"bad regex {p!r}: {e}") from e
        else:
            compiled.append((p, None))
    files = walk_files(base, sub, max_files=50000, globs=globs,
                       include_hidden=include_hidden)
    hits: dict[str, list[dict]] = {p: [] for p in patterns}
    total = 0
    scanned = 0
    bytes_seen = 0
    truncated = False
    for rel in files:
        fp = base / rel
        try:
            size = fp.stat().st_size
            if size > max_file_bytes:
                continue
            raw = fp.read_bytes()
        except OSError:
            continue
        if b"\x00" in raw[:8192]:
            continue
        text = raw.decode("utf-8", errors="replace")
        scanned += 1
        bytes_seen += len(raw)
        lines = text.splitlines()
        for idx, line in enumerate(lines):
            for label, rx in compiled:
                if len(hits[label]) >= max_hits:
                    truncated = True
                    continue
                found = bool(rx.search(line)) if rx else (label in line)
                if not found:
                    continue
                hit = {"file": rel, "line": idx + 1,
                       "text": _scrub(line.strip()[:300]), "pattern": label}
                if context > 0:
                    lo = max(0, idx - context)
                    hi = min(len(lines), idx + context + 1)
                    hit["context"] = [
                        {"line": i + 1, "text": _scrub(lines[i].strip()[:240])}
                        for i in range(lo, hi)]
                hits[label].append(hit)
                total += 1
        if total >= max_hits * len(patterns):
            truncated = True
            break
    return {"ok": True, "root": str(base), "patterns": patterns,
            "hits": hits, "total": total, "files_scanned": scanned,
            "bytes_scanned": bytes_seen, "truncated": truncated,
            "elapsed_ms": _ms(t0)}


def search(root: str, patterns: Any, dir: str = ".", globs: Any = None,
           max_hits: int = 200, context: int = 0,
           ignore_case: bool = False, regex: bool = True,
           include_hidden: bool = False) -> dict[str, Any]:
    base = validate_root(root)
    pats = [str(p) for p in _as_list(patterns) if str(p)]
    gl = [str(g) for g in _as_list(globs) if str(g)] or None
    return _scan(base, pats, sub=dir or ".", globs=gl,
                 max_hits=int(max_hits), context=int(context),
                 ignore_case=ignore_case, regex=regex,
                 include_hidden=include_hidden)


# --------------------------------------------------------------------------
# speed.context — one call returns the files the agent needs next
# --------------------------------------------------------------------------

def _important(base: Path, sub: str, globs: list[str] | None,
               limit: int) -> list[str]:
    files = walk_files(base, sub, max_files=50000, globs=globs)
    priority = ("readme", "pyproject.toml", "package.json", "pom.xml",
                "build.gradle", "cargo.toml", "go.mod", "requirements.txt",
                "dockerfile", "makefile", "plugin.yml", "config.yml")
    ranked = sorted(files, key=lambda p: (
        0 if any(p.lower().endswith(x) or p.lower().split("/")[-1] == x
                 for x in priority) else 1,
        0 if p.count("/") <= 2 else 1,
        len(p), p.lower()))
    return ranked[:limit]


def context(root: str, paths: Any = None, query: str = "",
            globs: Any = None, dir: str = ".", max_files: int = 24,
            max_chars: int = 160_000, max_lines: int = 500,
            include_tree: bool = True,
            include_hidden: bool = False) -> dict[str, Any]:
    t0 = time.perf_counter()
    base = validate_root(root)
    gl = [str(g) for g in _as_list(globs) if str(g)] or None
    wanted: list[str] = []
    if paths:
        for raw in _as_list(paths):
            p = resolve(base, str(raw))
            if p.is_dir():
                wanted.extend(walk_files(base, str(raw), max_files=5000,
                                         globs=gl,
                                         include_hidden=include_hidden))
            elif p.is_file():
                wanted.append(p.relative_to(base).as_posix())
    elif query:
        found = _scan(base, [query], sub=dir or ".", globs=gl,
                      max_hits=500, regex=True,
                      include_hidden=include_hidden)
        counts: dict[str, int] = {}
        for hit in found["hits"].get(query, []):
            counts[hit["file"]] = counts.get(hit["file"], 0) + 1
        wanted = sorted(counts, key=lambda p: (-counts[p], p.lower()))
    else:
        wanted = _important(base, dir or ".", gl, max_files)
    seen: set[str] = set()
    picked: list[str] = []
    for rel in wanted:
        if rel not in seen and len(picked) < max_files:
            seen.add(rel)
            picked.append(rel)
    files: list[dict] = []
    budget = max(1000, int(max_chars))
    total_chars = 0
    for rel in picked:
        if budget <= 0:
            break
        try:
            text = read_text(base / rel)
        except (OSError, ValueError):
            continue
        text = _scrub(text)
        lines = text.splitlines()
        truncated = len(lines) > max_lines or len(text) > budget
        if len(lines) > max_lines:
            text = "\n".join(lines[:max_lines])
        if len(text) > budget:
            text = text[:budget]
        total_chars += len(text)
        budget -= len(text)
        files.append({
            "path": rel,
            "lang": LANG.get(Path(rel).suffix.lower(), ""),
            "lines": len(lines),
            "chars": len(text),
            "truncated": truncated,
            "content": text,
        })
    all_files = walk_files(base, dir or ".", max_files=5000, globs=gl,
                           include_hidden=include_hidden)
    return {"ok": True, "root": str(base), "files": files,
            "file_count": len(files), "total_chars": total_chars,
            "tokens_est": math.ceil(total_chars / 4),
            "tree": tree_text(all_files, base.name) if include_tree else "",
            "tree_files": len(all_files), "elapsed_ms": _ms(t0)}


# --------------------------------------------------------------------------
# speed.blueprint — a whole complex structure in one call
# --------------------------------------------------------------------------

def blueprint(root: str, name: str = "Forge App", template: str = "python-package",
              package: str = "", files: Any = None, vars: Any = None,
              force: bool = False, dry_run: bool = False,
              backup: bool = False, atomic: bool = False) -> dict[str, Any]:
    t0 = time.perf_counter()
    base = validate_root(root, create=True)
    custom = files is not None
    try:
        made, used = _recipes.build(
            "custom" if custom else template, name, package,
            extra=files if isinstance(files, dict) else None,
            extra_vars={str(k): str(v) for k, v in (vars or {}).items()})
    except (ValueError, KeyError, TypeError) as e:
        return {"ok": False, "root": str(base), "error": f"{type(e).__name__}: {e}",
                "duration_ms": _ms(t0)}
    if not isinstance(made, dict) or not made:
        return {"ok": False, "root": str(base), "error": "blueprint is empty"}
    errors = []
    staged: dict[str, bytes] = {}
    skipped: list[str] = []
    cache: dict[str, Path] = {}
    for rel, content in made.items():
        rel = rel.replace("\\", "/").lstrip("/")
        try:
            target = resolve_cached(base, rel, cache)
        except (ValueError, PermissionError) as e:
            errors.append({"path": rel, "error": str(e)})
            continue
        if target.exists() and not force:
            skipped.append(rel)
            continue
        staged[rel] = str(content).encode("utf-8")
    if errors:
        return {"ok": False, "root": str(base), "errors": errors,
                "duration_ms": _ms(t0)}
    if dry_run:
        return {"ok": True, "root": str(base), "dry_run": True,
                "template": "custom" if custom else template,
                "would_write": sorted(staged), "skipped": skipped,
                "files": len(staged), "vars": used, "duration_ms": _ms(t0)}
    try:
        res = apply_batch(base, staged, backup=backup, atomic=atomic)
    except (OSError, ValueError, PermissionError) as e:
        return {"ok": False, "root": str(base), "error": f"{type(e).__name__}: {e}",
                "duration_ms": _ms(t0)}
    return {"ok": True, "root": str(base),
            "template": "custom" if custom else template,
            "files": len(res["written"]), "written": res["written"],
            "skipped": skipped, "bytes": res["bytes"],
            "backup": res.get("backup", ""), "atomic": res.get("atomic", atomic),
            "vars": used, "duration_ms": _ms(t0)}


def recipes() -> dict[str, Any]:
    return {"ok": True, "recipes": _recipes.list_recipes()}


# --------------------------------------------------------------------------
# speed.bench — prove the speedup on this machine
# --------------------------------------------------------------------------

def _median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def bench(root: str, files: int = 80, repeats: int = 2,
          payload: int = 600, call_overhead_ms: float = 2.0) -> dict[str, Any]:
    base = validate_root(root)
    n = max(5, min(int(files), 500))
    reps = max(1, min(int(repeats), 5))
    text = ("# forge speed bench\n" + "x" * max(20, int(payload))) + "\n"
    work = base / ".forge-speed-bench"
    t0 = time.perf_counter()
    try:
        if work.exists():
            shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True)
        seq_write: list[float] = []
        bat_write: list[float] = []
        bat_atomic: list[float] = []
        batch = {f"batch_{i}.txt": text.encode() for i in range(n)}
        for _ in range(reps):
            t = time.perf_counter()
            for i in range(n):
                (work / f"seq_{i}.txt").write_text(text, encoding="utf-8")
            seq_write.append(time.perf_counter() - t)
            for i in range(n):
                (work / f"seq_{i}.txt").unlink(missing_ok=True)
            t = time.perf_counter()
            apply_batch(work, batch, atomic=False)
            bat_write.append(time.perf_counter() - t)
            for i in range(n):
                (work / f"batch_{i}.txt").unlink(missing_ok=True)
            t = time.perf_counter()
            apply_batch(work, batch, atomic=True)
            bat_atomic.append(time.perf_counter() - t)
            for i in range(n):
                (work / f"batch_{i}.txt").unlink(missing_ok=True)
        seq_search: list[float] = []
        bat_search: list[float] = []
        patterns = ["needle", "line one", "line three", "here"]
        for _ in range(reps):
            for i in range(n):
                (work / f"s_{i}.txt").write_text(
                    f"line one\nthe needle is here {i}\nline three\n",
                    encoding="utf-8")
            from ..security.sandbox import Sandbox
            t = time.perf_counter()
            for pat in patterns:
                Sandbox(str(work)).search(pat)
            seq_search.append(time.perf_counter() - t)
            t = time.perf_counter()
            _scan(work, patterns, max_hits=5000)
            bat_search.append(time.perf_counter() - t)
            for i in range(n):
                (work / f"s_{i}.txt").unlink(missing_ok=True)
        # Batch patches: one call vs one edit call per file.
        seq_patch: list[float] = []
        bat_patch: list[float] = []
        for _ in range(reps):
            for i in range(n):
                (work / f"p_{i}.txt").write_text("value = 1\n", encoding="utf-8")
            t = time.perf_counter()
            for i in range(n):
                fp = work / f"p_{i}.txt"
                fp.write_text(fp.read_text(encoding="utf-8").replace("1", "2"),
                              encoding="utf-8")
            seq_patch.append(time.perf_counter() - t)
            for i in range(n):
                (work / f"p_{i}.txt").write_text("value = 1\n", encoding="utf-8")
            t = time.perf_counter()
            patch(str(work), [{"path": f"p_{i}.txt", "find": "1",
                               "replace": "2"} for i in range(n)],
                  diff=False, atomic=False)
            bat_patch.append(time.perf_counter() - t)
            for i in range(n):
                (work / f"p_{i}.txt").unlink(missing_ok=True)
        overhead = max(0.0, float(call_overhead_ms)) / 1000.0

        def section(seq: list[float], bat: list[float], calls: int) -> dict:
            sd, bd = _median(seq), _median(bat)
            se = sd + calls * overhead
            be = bd + overhead
            return {"sequential_disk_ms": round(sd * 1000, 2),
                    "batch_disk_ms": round(bd * 1000, 2),
                    "sequential_effective_ms": round(se * 1000, 2),
                    "batch_effective_ms": round(be * 1000, 2),
                    "speedup": round(se / max(be, 1e-9), 2)}

        return {
            "ok": True, "root": str(base), "files": n, "repeats": reps,
            "roundtrip_ms": round(float(call_overhead_ms), 2),
            "write": section(seq_write, bat_write, n),
            "write_atomic": section(seq_write, bat_atomic, n),
            "patch": section(seq_patch, bat_patch, n),
            "search_4_patterns": {
                "sequential_ms": round(_median(seq_search) * 1000, 2),
                "batch_ms": round(_median(bat_search) * 1000, 2),
                "speedup": round(_median(seq_search) / max(_median(bat_search), 1e-9), 2),
            },
            "elapsed_ms": _ms(t0),
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)
