"""FORGE pipe: stage contracts for the conveyor.

Each stage is a small deterministic function (ctx) -> ToolResult.
Stages use REAL engines only: project walk, quality.review, skills
loader/validator, knowledge store. No mocks, no hallucinated checks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from forge.core.result import ToolResult, timed

StageFn = Callable[[dict[str, Any]], ToolResult]


@dataclass
class Stage:
    name: str
    title: str
    fn: StageFn
    timeout_s: float = 120.0
    allow_fail: bool = False
    notes: str = ""


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


DEFAULT_STAGES: list[Stage] = [
    Stage("inspect", "1/4 Осмотр проекта", stage_inspect, 60.0,
          notes="структура, языки, сборка"),
    Stage("review", "2/4 Ревью кода", stage_review, 180.0,
          notes="confirmed = FAIL"),
    Stage("skills", "3/4 Проверка скиллов", stage_skills, 60.0,
          notes="все скиллы должны валидироваться"),
    Stage("knowledge", "4/4 База знаний", stage_knowledge, 60.0,
          allow_fail=True, notes="предупреждает, не валит"),
]
