"""Static code review: fast, deterministic, no model needed.

Finds: oversized files, TODO/FIXME debt, duplicated blocks,
empty catch blocks, System.out debugging leftovers.
Classifies per prompt 4.3: confirmed vs probable (we only emit
mechanical facts; severity labels are explicit heuristics).
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", "build",
             ".gradle", "target", "out", ".idea"}
CODE_EXTS = {".java", ".py", ".js", ".ts", ".tsx", ".kt", ".go", ".rs"}
MAX_FILE_BYTES = 4 * 1024 * 1024  # как у взрослых: минифицированные бандлы не читаем
IGNORE_MARK = "forge-ignore"  # `# forge-ignore` / `// forge-ignore[: rule]` в конце строки


def _ignored(line: str, rule: str) -> bool:
    """Строковое подавление в стиле trunk-ignore, только честное: видно в коде."""
    i = line.find(IGNORE_MARK)
    if i < 0:
        return False
    tail = line[i + len(IGNORE_MARK):].strip().lstrip(":").strip()
    return not tail or tail.split()[0].strip(",") == rule


def review(root: str | Path, max_files: int = 500,
           suppress: list[dict] | None = None,
           only: set[str] | None = None) -> dict:
    """suppress: [{"rule":..., "file":... (rel path), "reason":...}].
    only: подмножество rel-путей (git changed) — hold-the-line как у взрослых.

    Подавление БЕЗ причины не действует. Подавленные находки остаются
    в findings с флагом suppressed (видны, но не считаются confirmed).
    Обход безопасен: skip-dir'ы, игнор ошибок доступа, лимит файлов,
    пропуск файлов >4МБ, без симлинков.
    """
    base = Path(root)
    files: list[Path] = []
    for dirpath, dirnames, filenames in __import__("os").walk(base, onerror=lambda e: None):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if Path(fn).suffix in CODE_EXTS:
                rel = str((Path(dirpath) / fn).relative_to(base)).replace("\\", "/")
                if only is not None and rel not in only:
                    continue
                try:
                    if (Path(dirpath) / fn).stat().st_size > MAX_FILE_BYTES:
                        continue  # минифицированный бандл — не читаем
                except OSError:
                    continue
                files.append(Path(dirpath) / fn)
                if len(files) >= max_files:
                    break
        if len(files) >= max_files:
            break  # дальше не идём: лимит защищает от гигантских деревьев
    findings: list[dict] = []
    total_lines = 0
    for fp in files:
        try:
            text = fp.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeError):
            continue
        rel = str(fp.relative_to(base)).replace("\\", "/")
        lines = text.splitlines()
        total_lines += len(lines)
        if len(lines) > 800:
            findings.append({"level": "probable", "rule": "oversized-file",
                             "file": rel, "detail": f"{len(lines)} lines"})
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if re.search(r"\b(TODO|FIXME|XXX|HACK)\b", s) and not _ignored(s, "debt-marker"):
                findings.append({"level": "confirmed", "rule": "debt-marker",
                                 "file": rel, "detail": f"L{i}: {s[:100]}"})
            if re.match(r"catch\s*\(.*\)\s*\{\s*\}$", s) and not _ignored(s, "empty-catch"):
                findings.append({"level": "probable", "rule": "empty-catch",
                                 "file": rel, "detail": f"L{i}"})
            if ("System.out.print" in s or "printStackTrace()" in s) and not _ignored(s, "debug-leftover"):
                findings.append({"level": "probable", "rule": "debug-leftover",
                                 "file": rel, "detail": f"L{i}: {s[:80]}"})
    findings.extend(_duplicates(files, base))
    suppressed = 0
    for f in findings:
        for s in suppress or []:
            if not s.get("reason"):
                continue
            ff = str(f.get("file", "")).replace("\\", "/")
            sf = str(s.get("file", "")).replace("\\", "/")
            if f.get("rule") == s.get("rule") and ff == sf:
                f["suppressed"] = True
                f["suppress_reason"] = s["reason"]
                suppressed += 1
                break
    confirmed = sum(1 for f in findings
                    if f["level"] == "confirmed" and not f.get("suppressed"))
    return {"files": len(files), "lines": total_lines,
            "confirmed": confirmed,
            "probable": len(findings) - confirmed - suppressed,
            "suppressed": suppressed, "findings": findings[:100]}


def _duplicates(files: list[Path], base: Path) -> list[dict]:
    seen: dict[str, list[str]] = {}
    out = []
    for fp in files:
        try:
            lines = [l.strip() for l in
                     fp.read_text(encoding="utf-8", errors="strict").splitlines()]
        except (OSError, UnicodeError):
            continue
        lines = [l for l in lines if len(l) > 20 and not l.startswith(("//", "#", "*"))]
        for i in range(len(lines) - 5):
            h = hashlib.md5("\n".join(lines[i:i + 5]).encode()).hexdigest()
            seen.setdefault(h, []).append(f"{fp.relative_to(base)}:{i + 1}")
            if len(seen[h]) == 2:
                out.append({"level": "probable", "rule": "duplicate-block",
                            "file": str(fp.relative_to(base)),
                            "detail": f"5-line dup also at {seen[h][0]}"})
                if len(out) >= 20:
                    return out
    return out
