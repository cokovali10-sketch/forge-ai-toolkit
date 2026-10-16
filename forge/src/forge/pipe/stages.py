"""FORGE pipe: stage contracts for the conveyor.

Each stage is a small deterministic function (ctx) -> ToolResult.
Stages use REAL engines only: project walk, quality.review, skills
loader/validator, knowledge store. No mocks, no hallucinated checks.

Fingerprint (unique tech): every cacheable stage declares WHAT it reads
as a content hash. The runner skips stages whose inputs did not change —
plain `run` is incremental like Cargo/Bazel, no flags needed.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from forge.core.result import ToolResult, timed

StageFn = Callable[[dict[str, Any]], ToolResult]
PrintFn = Callable[[dict[str, Any]], str | None]


@dataclass
class Stage:
    name: str
    title: str
    fn: StageFn
    timeout_s: float = 120.0
    allow_fail: bool = False
    notes: str = ""
    fingerprint: PrintFn | None = None  # None = всегда запускать
    heavy: bool = False  # тяжёлые идут строго после быстрых и только на зелёном


def tree_hash(root: str | Path, exts: set[str] | None = None) -> str:
    """sha1(relpath + size + mtime) по файлам. Дешево, честно, детерминировано."""
    h = hashlib.sha1()
    base = Path(root)
    if not base.is_dir():
        return "no-dir"
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            if fn in ("forge-pipe-checkpoint.json", "forge-pipe-report.json",
                      ".forge-pipe-history.jsonl"):
                continue
            if exts is not None and Path(fn).suffix.lower() not in exts:
                continue
            fp = Path(dirpath) / fn
            try:
                st = fp.stat()
                h.update(f"{fp.relative_to(base)}|{st.st_size}|{st.st_mtime_ns}\n".encode())
            except OSError:
                pass
    return h.hexdigest()[:16]


CODE_EXTS = {".py", ".java", ".js", ".ts", ".tsx", ".kt", ".go", ".rs"}


def _supp_hash(target: str | Path) -> str:
    """Хэш файла подавлений: поменялись правила — ревью пересчитывается."""
    import hashlib as _hl
    try:
        return _hl.sha1(Path(target, ".forge-suppress.json").read_bytes()).hexdigest()[:16]
    except OSError:
        return "no-suppress"


SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__",
             "build", "target", "out", ".gradle", ".idea", "dist"}


def stage_inspect(ctx: dict[str, Any]) -> ToolResult:
    def run() -> dict:
        root = Path(ctx["target"])
        if not root.is_dir():
            raise NotADirectoryError(str(root))
        by_ext: dict[str, int] = {}
        lines = 0
        build: list[str] = []
        n_files = 0
        for dirpath, dirnames, filenames in __import__("os").walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                n_files += 1
                suf = Path(fn).suffix.lower() or "<noext>"
                by_ext[suf] = by_ext.get(suf, 0) + 1
                if fn in ("pom.xml", "build.gradle", "build.gradle.kts",
                          "package.json", "pyproject.toml", "setup.py",
                          "plugin.yml", "paper-plugin.yml", "Dockerfile"):
                    rel = str((Path(dirpath) / fn).relative_to(root))
                    if rel not in build:
                        build.append(rel)
                fp = Path(dirpath) / fn
                if fp.suffix in (".py", ".java", ".js", ".ts", ".go", ".rs"):
                    try:
                        with open(fp, "rb") as fh:
                            lines += sum(1 for _ in fh)
                    except OSError:
                        pass
        return {"files": n_files, "by_ext": by_ext, "code_lines": lines,
                "build_files": build[:20]}
    return timed(run)


def stage_review(ctx: dict[str, Any]) -> ToolResult:
    import json as _json
    from forge.quality.review import review
    supp: list = []
    sp = Path(ctx["target"]) / ".forge-suppress.json"
    if sp.is_file():
        try:
            supp = _json.loads(sp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            supp = []
    res = timed(review, ctx["target"], 500, supp)
    if not res.ok:
        return res
    data = res.result if isinstance(res.result, dict) else {}
    findings = data.get("findings", []) if isinstance(data, dict) else []
    confirmed = [f for f in findings
                 if f.get("level") == "confirmed" and not f.get("suppressed")]
    n_supp = data.get("suppressed", 0) if isinstance(data, dict) else 0
    if confirmed:
        res.status = "FAILED"
        res.error = {"message": f"{len(confirmed)} confirmed findings",
                     "sample": confirmed[:5]}
    else:
        res.warnings = [f"{len(findings)} findings, {n_supp} suppressed "
                        f"(see .forge-suppress.json)"]
    return res


def stage_skills(ctx: dict[str, Any]) -> ToolResult:
    def run() -> dict:
        from forge.skills.loader import load_skills, validate_skill
        skills = load_skills(Path(ctx["forge_root"]) / "skills")
        bad: dict[str, list[str]] = {}
        for name, sk in skills.items():
            errs = validate_skill(sk)
            if errs:
                bad[name] = errs
        if bad:
            raise ValueError(f"invalid skills: {sorted(bad)}")
        return {"skills": sorted(skills), "checked": len(skills)}
    return timed(run)


def stage_knowledge(ctx: dict[str, Any]) -> ToolResult:
    def run() -> dict:
        from forge.knowledge.store import KnowledgeStore
        ks = KnowledgeStore()
        seed = Path(ctx["forge_root"]) / "knowledge" / "seed.jsonl"
        docs = 0
        if seed.is_file():
            docs = ks.load_jsonl(seed)
        probe = ks.search("java plugin build", limit=3)
        return {"docs": docs, "probe_hits": len(probe)}
    r = timed(run)
    if r.ok and isinstance(r.result, dict) and r.result.get("docs", 0) == 0:
        r.warnings = ["knowledge base is empty (seed only)"]
    return r


DEFAULT_STAGES: list[Stage] = [    Stage("inspect", "1/4 Осмотр проекта", stage_inspect, 60.0,
          notes="структура, языки, сборка",
          fingerprint=lambda c: tree_hash(c["target"])),
    Stage("review", "2/4 Ревью кода", stage_review, 180.0,
          notes="confirmed = FAIL",
          fingerprint=lambda c: tree_hash(c["target"], CODE_EXTS) + _supp_hash(c["target"])),
    Stage("skills", "3/4 Проверка скиллов", stage_skills, 60.0,
          notes="все скиллы должны валидироваться",
          fingerprint=lambda c: tree_hash(Path(c["forge_root"]) / "skills")),
    Stage("knowledge", "4/4 База знаний", stage_knowledge, 60.0,
          allow_fail=True, notes="предупреждает, не валит",
          fingerprint=lambda c: tree_hash(Path(c["forge_root"]) / "knowledge",
                                           {".jsonl"})),
]


def _find_java() -> str:
    import os as _os
    cands = [_os.environ.get("FORGE_JAVA21", ""),
             r"C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot\bin\java.exe"]
    return next((c for c in cands if c and Path(c).is_file()), "")


def stage_lab_e2e(ctx: dict[str, Any]) -> ToolResult:
    """Тяжёлая стадия: настоящий Purpur + сборка фикстуры (минуты).

    Без jar/JDK честно отвечает ERROR «env not ready» вместо падения.
    В DEFAULT_STAGES не входит — только --heavy / --only lab-e2e.
    """
    def run() -> dict:
        from forge.lab import runner as _r
        root = Path(ctx["forge_root"])
        jars = sorted((root.parent / "lab-servers").glob("purpur-*.jar"))
        if not jars:
            raise FileNotFoundError("env not ready: нет lab-servers/purpur-*.jar")
        java = _find_java()
        if not java:
            raise FileNotFoundError("env not ready: нет JDK21 (FORGE_JAVA21)")
        rep = _r.e2e_fixture(root.parent / "lab-runs", str(jars[0]),
                             root / "tests" / "fixture-plugin" / "src",
                             java_bin=java)
        if not rep.get("ok"):
            bad = [c.get("stage", "?") for c in rep.get("checks", [])
                   if not c.get("ok")]
            raise RuntimeError(f"e2e failed: {bad or 'unknown'}")
        return {"checks": len(rep.get("checks", []))}
    return timed(run)


HEAVY_STAGES: list[Stage] = [
    Stage("lab-e2e", "5/5 Lab E2E (тяжёлая)", stage_lab_e2e, 1500.0,
          notes="Purpur + JDK21, минуты; только --heavy",
          fingerprint=lambda c: tree_hash(
              Path(c["forge_root"]) / "tests" / "fixture-plugin",
              CODE_EXTS) + tree_hash(
              Path(c["forge_root"]) / "src" / "forge" / "lab",
              {".py"}),
          heavy=True),
]

ALL_STAGES: dict[str, Stage] = {s.name: s for s in DEFAULT_STAGES + HEAVY_STAGES}
