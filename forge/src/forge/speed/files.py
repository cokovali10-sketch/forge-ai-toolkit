"""Fast, safe filesystem primitives for the Speed department.

No third-party deps. Every path is resolved inside an explicit root; writes
are staged and applied with os.replace, with rollback when a batch fails.
"""
from __future__ import annotations

import fnmatch
import os
import tempfile
import time
from pathlib import Path

SKIP_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".gradle", ".idea", ".vs", "dist", "build", "target", "out",
    ".forge-speed-backup", ".forge-speed-bench",
}
TEXT_LIMIT = 2_000_000
MAX_FILES = 2_000
MAX_BYTES = 24 * 1024 * 1024

LANG = {
    ".py": "python", ".pyi": "python", ".js": "javascript", ".mjs": "javascript",
    ".cjs": "javascript", ".ts": "typescript", ".tsx": "typescript",
    ".jsx": "javascript", ".java": "java", ".kt": "kotlin", ".kts": "kotlin",
    ".go": "go", ".rs": "rust", ".c": "c", ".h": "c", ".cpp": "cpp",
    ".hpp": "cpp", ".cs": "csharp", ".rb": "ruby", ".php": "php",
    ".swift": "swift", ".sh": "shell", ".ps1": "powershell",
    ".html": "html", ".css": "css", ".scss": "scss", ".vue": "vue",
    ".sql": "sql", ".json": "json", ".yml": "yaml", ".yaml": "yaml",
    ".toml": "toml", ".xml": "xml", ".md": "markdown", ".txt": "text",
}


def validate_root(root: str | Path, create: bool = False) -> Path:
    """Resolve a workspace root; optionally create it. Never a drive root."""
    raw = Path(root).expanduser()
    if raw.exists() and not raw.is_dir():
        raise ValueError(f"root is not a directory: {raw}")
    if not raw.exists():
        if not create:
            raise FileNotFoundError(f"root does not exist: {raw}")
        raw.mkdir(parents=True, exist_ok=True)
    p = raw.resolve()
    if p == Path(p.anchor):
        raise ValueError("refusing to use a filesystem root as workspace")
    low = str(p).lower()
    denylist = ("c:\\windows", "c:\\program files", "c:\\program files (x86)")
    if any(low == d or low.startswith(d + "\\") for d in denylist):
        raise ValueError(f"refusing to write to a system directory: {p}")
    return p


def resolve(root: Path, rel: str) -> Path:
    """Resolve rel inside root; reject traversal and symlink escapes."""
    if not rel or not str(rel).strip():
        raise ValueError("empty path")
    p = (root / str(rel)).resolve()
    if p != root and root not in p.parents:
        raise PermissionError(f"outside workspace: {rel}")
    return p


def resolve_cached(root: Path, rel: str, cache: dict[str, Path]) -> Path:
    """Same guarantee as resolve(), but resolve each parent dir only once.

    A batch usually touches many files in the same directories; caching parent
    realpaths removes one full resolve() per file (a measurable win on Windows).
    """
    if not rel or not str(rel).strip():
        raise ValueError("empty path")
    p = root / str(rel)
    parent = p.parent
    key = str(parent)
    real_parent = cache.get(key)
    if real_parent is None:
        real_parent = parent.resolve()
        if real_parent != root and root not in real_parent.parents:
            raise PermissionError(f"outside workspace: {rel}")
        cache[key] = real_parent
    target = real_parent / p.name
    if target.is_symlink():
        target = target.resolve()
        if target != root and root not in target.parents:
            raise PermissionError(f"outside workspace: {rel}")
    return target


def relpath(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def walk_files(root: Path, sub: str = ".", max_files: int = 20000,
               globs: list[str] | None = None,
               include_hidden: bool = False) -> list[str]:
    """One fast os.walk pass. Returns POSIX relative paths, sorted."""
    base = resolve(root, sub)
    if not base.is_dir():
        raise ValueError(f"not a directory: {sub}")
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in SKIP_DIRS and (include_hidden or not d.startswith(".")))
        for fn in sorted(filenames):
            if not include_hidden and fn.startswith("."):
                continue
            fp = Path(dirpath) / fn
            rel = relpath(root, fp)
            if globs and not any(fnmatch.fnmatch(rel, g)
                                 or fnmatch.fnmatch(fn, g) for g in globs):
                continue
            out.append(rel)
            if len(out) >= max_files:
                return out
    return out


def read_text(path: Path, limit: int = TEXT_LIMIT) -> str:
    """Read text without loading huge/binary files. Raises ValueError."""
    try:
        size = path.stat().st_size
    except OSError as e:
        raise ValueError(f"cannot stat {path.name}: {e}") from e
    if size > limit:
        raise ValueError(f"file too large: {size} bytes")
    try:
        raw = path.read_bytes()
    except OSError as e:
        raise ValueError(f"cannot read {path.name}: {e}") from e
    if b"\x00" in raw[:8192]:
        raise ValueError("binary file")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


def _write_one(target: Path, data: bytes, ensure_parent: bool = True) -> None:
    if ensure_parent:
        target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(target.parent), prefix=".forge-",
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, target)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def apply_batch(root: Path, staged: dict[str, bytes | None],
                backup: bool = False, atomic: bool = True) -> dict:
    """Write/delete many files.

    atomic=True keeps old content in memory (up to MAX_BYTES) and rolls the
    whole batch back if any write fails. atomic=False is the fast path:
    direct writes, no originals, no rollback.
    """
    if len(staged) > MAX_FILES:
        raise ValueError(f"too many files in one batch: {len(staged)}")
    total = sum(len(v) for v in staged.values() if v is not None)
    if total > MAX_BYTES:
        raise ValueError(f"batch too large: {total} bytes")
    if backup:
        atomic = True
    originals: dict[str, bytes | None] = {}
    targets: dict[str, Path] = {}
    cache: dict[str, Path] = {}
    for rel, data in staged.items():
        t = resolve_cached(root, rel, cache)
        if any(part == ".git" for part in t.relative_to(root).parts):
            raise PermissionError(f"refusing to write inside .git: {rel}")
        targets[rel] = t
        if atomic:
            try:
                originals[rel] = t.read_bytes() if t.is_file() else None
            except OSError:
                originals[rel] = None
    backup_dir = ""
    if backup:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        bdir = root / ".forge-speed-backup" / stamp
        for rel, old in originals.items():
            if old is None:
                continue
            dst = bdir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(old)
        backup_dir = str(bdir)
    written: list[dict] = []
    parents_done: set[str] = set()
    try:
        for rel, data in staged.items():
            t = targets[rel]
            if data is None:
                if t.is_file():
                    t.unlink()
                written.append({"path": rel, "status": "deleted", "bytes": 0})
            elif atomic:
                key = str(t.parent)
                if key not in parents_done:
                    t.parent.mkdir(parents=True, exist_ok=True)
                    parents_done.add(key)
                _write_one(t, data, ensure_parent=False)
                written.append({"path": rel, "status": "written",
                                "bytes": len(data)})
            else:
                key = str(t.parent)
                if key not in parents_done:
                    t.parent.mkdir(parents=True, exist_ok=True)
                    parents_done.add(key)
                t.write_bytes(data)
                written.append({"path": rel, "status": "written",
                                "bytes": len(data)})
    except Exception:
        if atomic:
            # best-effort rollback of everything touched so far
            for rel, old in originals.items():
                t = targets[rel]
                try:
                    if old is None:
                        if t.is_file():
                            t.unlink()
                    else:
                        _write_one(t, old)
                except OSError:
                    pass
        raise
    return {"written": written, "backup": backup_dir, "bytes": total,
            "atomic": atomic}


def tree_text(paths: list[str], root_name: str = "") -> str:
    """Render a compact ASCII tree from relative paths."""
    tree: dict = {}
    for p in sorted(paths):
        cur = tree
        parts = p.split("/")
        for part in parts:
            cur = cur.setdefault(part, {})
    lines: list[str] = [root_name or "."]

    def walk(node: dict, prefix: str = "") -> None:
        items = sorted(node.items(), key=lambda kv: (not kv[1], kv[0].lower()))
        for i, (name, child) in enumerate(items):
            last = i == len(items) - 1
            lines.append(prefix + ("└── " if last else "├── ") + name)
            if child:
                walk(child, prefix + ("    " if last else "│   "))

    walk(tree)
    return "\n".join(lines)
