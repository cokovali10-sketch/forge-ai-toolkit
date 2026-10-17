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
from dataclasses import dataclass
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
    n = 0
    for dirpath, dirnames, filenames in os.walk(base, onerror=lambda e: None):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            if fn in ("forge-pipe-checkpoint.json", "forge-pipe-report.json",
                      ".forge-pipe-history.jsonl"):
                continue
            if exts is not None and Path(fn).suffix.lower() not in exts:
                continue
            n += 1
            if n > 30000:
                h.update(b"|CAPPED|")
                dirnames[:] = []
                break
            fp = Path(dirpath) / fn
            try:
                st = fp.stat()
                h.update(f"{fp.relative_to(base)}|{st.st_size}|{st.st_mtime_ns}\n".encode())
            except OSError:
                pass
        if n > 30000:
            break
    return h.hexdigest()[:16]


CODE_EXTS = {".py", ".java", ".js", ".ts", ".tsx", ".kt", ".go", ".rs"}
LANG_EXTS = CODE_EXTS | {".jsx", ".mjs", ".cjs", ".cpp", ".hpp", ".cc",
                         ".hh", ".c", ".h"}


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
        capped = False
        for dirpath, dirnames, filenames in __import__("os").walk(root, onerror=lambda e: None):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                n_files += 1
                if n_files > 30000:
                    capped = True
                    dirnames[:] = []
                    break
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
            if capped:
                break
        out = {"files": n_files, "by_ext": by_ext, "code_lines": lines,
               "build_files": build[:20]}
        if capped:
            out["capped"] = "дерево >30000 файлов: осмотр частичный"
        return out
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
    res = timed(review, ctx["target"], 500, supp, ctx.get("only"))
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
        docs = 0
        for fn in ("seed.jsonl", "mined.jsonl"):
            p = Path(ctx["forge_root"]) / "knowledge" / fn
            if p.is_file():
                docs += ks.load_jsonl(p)
        probe = ks.search("java plugin build", limit=3)
        return {"docs": docs, "probe_hits": len(probe)}
    r = timed(run)
    if r.ok and isinstance(r.result, dict) and r.result.get("docs", 0) == 0:
        r.warnings = ["knowledge base is empty (seed only)"]
    return r


def git_changed(target: str | Path) -> set[str] | None:
    """Изменённые файлы (staged + unstaged + untracked). None = не git."""
    import subprocess
    try:
        r = subprocess.run(["git", "status", "--short"], capture_output=True,
                           text=True, timeout=30, cwd=str(target))
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    out = set()
    for line in r.stdout.splitlines():
        p = line[3:].strip().strip('"')
        if " -> " in p:  # rename: берём новое имя
            p = p.split(" -> ")[-1].strip()
        if p:
            out.add(p.replace("\\", "/"))
    return out


def _review_fp(ctx: dict[str, Any]) -> str:
    only = ctx.get("only")
    if only is not None:
        h = hashlib.sha1()
        base = Path(ctx["target"])
        for rel in sorted(only):
            try:
                h.update(f"{rel}|{(base / rel).stat().st_mtime_ns}\n".encode())
            except OSError:
                h.update(f"{rel}|gone\n".encode())
        return "changed:" + h.hexdigest()[:16]
    return tree_hash(ctx["target"], CODE_EXTS) + _supp_hash(ctx["target"])

def stage_langs(ctx: dict[str, Any]) -> ToolResult:
    """Языки проекта: detect -> lint каждого найденного. Ошибка синтаксиса = FAIL,
    нет тулчейна = warning. Дешёвый и честный gate перед тяжёлыми стадиями."""
    warns: list[str] = []

    def run() -> dict:
        from forge.langs import LANGS
        found: dict[str, Any] = {}
        problems: list[str] = []
        for lid, mod in LANGS.items():
            d = mod.detect(ctx["target"])
            if not d.get("present"):
                continue
            found[lid] = {"markers": d.get("markers", []),
                          "files": d.get("files", 0)}
            r = mod.lint(ctx["target"])
            warns.extend(f"{lid}: {w}" for w in r.warnings)
            if r.status != "SUCCESS":
                detail = (r.error or {}).get("message", r.status) if isinstance(r.error, dict) else r.status
                problems.append(f"{lid}: {detail}"[:400])
        if problems:
            raise RuntimeError("; ".join(problems)[:1500])
        return {"languages": found}
    r = timed(run)
    if r.ok and warns:
        r.warnings = warns[:12]
    return r


def stage_clean_code(ctx: dict[str, Any]) -> ToolResult:
    """Советник по чистому коду: длинные функции, вложенность, дубли,
    магические числа, God-классы. Предупреждает, не валит (allow_fail):
    агент получает готовый план рефакторинга, поведение не проверяется тут."""
    warns: list[str] = []

    def run() -> dict:
        from forge.refactor.api import inspect as _inspect
        res = _inspect(ctx["target"])
        if not res.get("ok", True):
            return {"issues": 0}
        if "files_analyzed" in res:
            sev = {"high": 0, "medium": 0, "low": 0}
            kinds: dict[str, int] = {}
            for f in res["files_analyzed"]:
                for i in f.get("issues", []):
                    sev[i["severity"]] = sev.get(i["severity"], 0) + 1
                    kinds[i["kind"]] = kinds.get(i["kind"], 0) + 1
            total = res.get("total_issues", 0)
            score = res.get("score", 100)
            if total:
                warns.append(f"чистый код: {total} замечаний, здоровье {score}/100 "
                             f"(high={sev['high']}, medium={sev['medium']}, "
                             f"low={sev['low']}); см. skill refactor-expert")
                top = sorted(kinds.items(), key=lambda kv: -kv[1])[:5]
                warns.append("виды: " + ", ".join(f"{k}×{v}" for k, v in top))
            return {"issues": total, "score": score, "by_severity": sev, "by_kind": kinds}
        return {"issues": res.get("total", 0)}
    r = timed(run)
    if r.ok and warns:
        r.warnings = warns[:12]
    return r


def stage_secrets(ctx: dict[str, Any]) -> ToolResult:
    """Утечки секретов: FAIL только на high (ключи/токены/приватные ключи).

    Находки medium/low (напр. `password = "..."`) — предупреждение, не провал:
    инструмент работает на любом чужом проекте и не должен валить из-за эвристики.
    Полный секрет в отчёт не попадает — только маска. Строку с маркером
    `forge:allow-secret` сканер пропускает.
    """
    from forge.kit.secrets import scan_secrets
    res = timed(lambda: scan_secrets(ctx["target"]))
    if not res.ok:
        return res
    data = res.result if isinstance(res.result, dict) else {}
    findings = data.get("findings", []) if isinstance(data, dict) else []
    high = [f for f in findings if f.get("severity") == "high"]
    if high:
        res.status = "FAILED"
        res.error = {"message": f"{len(high)} секрет(ов) высокой важности",
                     "sample": high[:5]}
    elif findings:
        res.warnings = [f"{len(findings)} потенциальных секрет(ов) "
                        f"medium/low — `forge secrets .`"]
    return res


DEFAULT_STAGES: list[Stage] = [
    Stage("inspect", "1/8 Осмотр проекта", stage_inspect, 60.0,
          notes="структура, языки, сборка",
          fingerprint=lambda c: tree_hash(c["target"])),
    Stage("secrets", "2/8 Секреты (утечки)", stage_secrets, 120.0,
          notes="high = FAIL, medium/low = предупреждение",
          fingerprint=lambda c: tree_hash(c["target"])),
    Stage("review", "3/8 Ревью кода", stage_review, 180.0,
          notes="confirmed = FAIL",
          fingerprint=lambda c: _review_fp(c)),
    Stage("skills", "4/8 Проверка скиллов", stage_skills, 60.0,
          notes="все скиллы должны валидироваться",
          fingerprint=lambda c: tree_hash(Path(c["forge_root"]) / "skills")),
    Stage("knowledge", "5/8 База знаний", stage_knowledge, 60.0,
          allow_fail=True, notes="предупреждает, не валит",
          fingerprint=lambda c: tree_hash(Path(c["forge_root"]) / "knowledge",
                                           {".jsonl"})),
    Stage("langs", "6/8 Языки проекта", stage_langs, 600.0,
          notes="lint найденных языков (python/js/rust/cpp/go)",
          fingerprint=lambda c: tree_hash(c["target"], LANG_EXTS)),
    Stage("clean-code", "7/8 Чистый код", stage_clean_code, 120.0,
          allow_fail=True, notes="советник: длинные функции, вложенность, дубли",
          fingerprint=lambda c: tree_hash(c["target"], CODE_EXTS)),
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
    Stage("lab-e2e", "8/8 Lab E2E (тяжёлая)", stage_lab_e2e, 1500.0,
          notes="Purpur + JDK21, минуты; только --heavy",
          fingerprint=lambda c: tree_hash(
              Path(c["forge_root"]) / "tests" / "fixture-plugin",
              CODE_EXTS) + tree_hash(
              Path(c["forge_root"]) / "src" / "forge" / "lab",
              {".py"}),
          heavy=True),
]

ALL_STAGES: dict[str, Stage] = {s.name: s for s in DEFAULT_STAGES + HEAVY_STAGES}
