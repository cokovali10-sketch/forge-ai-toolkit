"""FORGE knowledge miner: репозиторий -> факты, без ИИ и выдумок.

Сканирует ТОЛЬКО проверяемое: файлы сборки, манифесты, CI.
Каждая запись — наблюдаемый факт (версия, зависимость, инструмент),
а не мнение. Источник помечается forge-miner:<repo> для аудита.
Домены любые: java, minecraft, frontend, python, build, devops, testing.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as _ET

VERSION = "0.3.0"


def _entry(domain: str, title: str, body: str, repo: str) -> dict[str, Any]:
    return {"domain": domain, "title": title, "body": body,
            "source": f"forge-miner:{repo}", "version": VERSION}


def _read(p: Path, limit: int = 512 * 1024) -> str:
    """Только чтение, только первые 512КБ. Никаких записей, сети, запусков."""
    try:
        if p.stat().st_size > limit * 4:
            return ""  # гигантские файлы (lock, бандлы) не трогаем вообще
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read(limit)
    except OSError:
        return ""


def _mine_gradle(root: Path, repo: str, out: list) -> None:
    w = root / "gradle" / "wrapper" / "gradle-wrapper.properties"
    t = _read(w)
    m = re.search(r"gradle-(\d+\.\d+)", t)
    if m:
        out.append(_entry("build", f"{repo}: Gradle {m.group(1)} (wrapper)",
                          f"Pinned via gradle-wrapper.properties: {m.group(1)}. "
                          f"Builds must use ./gradlew, never a system Gradle.", repo))
    bg = _read(root / "build.gradle") + _read(root / "build.gradle.kts")
    for pat, what in ((r"paperweight|paper-api", "Paper API"),
                      (r"junit|jupiter|mockito|mockbukkit", "JVM tests"),
                      (r"shadowJar|shadow\s", "Shadow/fat-jar packaging")):
        if re.search(pat, bg, re.I):
            out.append(_entry("build", f"{repo}: uses {what}",
                              f"Detected in build script ({what}).", repo))


def _mine_maven(root: Path, repo: str, out: list) -> None:
    p = root / "pom.xml"
    t = _read(p)
    if not t.strip():
        return
    try:
        xml = _ET.fromstring(t)
    except _ET.ParseError:
        return
    ns = {"m": "http://maven.apache.org/POM/4.0.0"}
    rel = (xml.findtext("m:properties/m:maven.compiler.release", namespaces=ns)
           or xml.findtext("m:properties/m:java.version", namespaces=ns)
           or xml.findtext("m:properties/m:jdk.version", namespaces=ns))
    if rel:
        out.append(_entry("java", f"{repo}: targets Java {rel}",
                          f"pom.xml pins compiler release to {rel}. "
                          f"Build/CI must run a matching JDK.", repo))
    deps = " ".join(a.findtext("m:artifactId", default="", namespaces=ns) or ""
                    for a in xml.findall(".//m:dependency", namespaces=ns))
    if re.search(r"junit|assertj|mockito", deps, re.I):
        out.append(_entry("testing", f"{repo}: JVM test stack present",
                          f"pom.xml declares test deps ({deps.strip()[:120]}). "
                          f"Run: mvn -q test.", repo))
    if "paper-api" in deps or "spigot-api" in deps:
        out.append(_entry("minecraft", f"{repo}: Bukkit-family plugin",
                          "pom.xml depends on paper-api/spigot-api. "
                          "Needs plugin.yml + Java 17+ toolchain.", repo))


def _mine_node(root: Path, repo: str, out: list) -> None:
    try:
        pkg = json.loads(_read(root / "package.json") or "{}")
    except ValueError:
        return
    if not isinstance(pkg, dict) or "name" not in pkg:
        return
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    for dep, label in (("react", "React"), ("typescript", "TypeScript"),
                       ("tailwindcss", "Tailwind CSS"), ("vite", "Vite"),
                       ("next", "Next.js"), ("vue", "Vue")):
        if dep in deps:
            out.append(_entry("frontend", f"{repo}: uses {label} {deps[dep]}",
                              f"package.json pins {dep}@{deps[dep]}. "
                              f"Install: npm ci (lockfile), never plain install in CI.", repo))
    eng = (pkg.get("engines", {}) or {}).get("node", "")
    if eng:
        out.append(_entry("frontend", f"{repo}: requires Node {eng}",
                          f"package.json engines.node = {eng}. "
                          f"CI must pin the same major.", repo))


def _mine_python(root: Path, repo: str, out: list) -> None:
    t = _read(root / "pyproject.toml")
    m = re.search(r'requires-python\s*=\s*["\']([^"\']+)', t)
    if m:
        out.append(_entry("python", f"{repo}: requires Python {m.group(1)}",
                          f"pyproject.toml requires-python = {m.group(1)}. "
                          f"Use venv + pinned interpreter.", repo))
    req = t + "\n" + _read(root / "requirements.txt") + "\n" + _read(root / "setup.py")
    if re.search(r"pytest|unittest|tox|nox", req, re.I):
        out.append(_entry("testing", f"{repo}: Python test tooling present",
                          "pytest/unittest/tox detected. Run: pytest -q.", repo))
    if re.search(r"fastapi|flask|django|aiohttp", req, re.I):
        out.append(_entry("python", f"{repo}: web framework present",
                          "A web framework is declared — check ports, CORS and "
                          "auth before exposing.", repo))


def _mine_minecraft(root: Path, repo: str, out: list) -> None:
    for fn in ("plugin.yml", "paper-plugin.yml"):
        t = _read(root / "src" / "main" / "resources" / fn)
        if not t.strip():
            continue
        m = re.search(r"api-version:\s*['\"]?([\d.]+)", t)
        if m:
            out.append(_entry("minecraft", f"{repo}: targets API {m.group(1)}",
                              f"{fn} declares api-version {m.group(1)}. "
                              f"Server jar must match; never mix Bukkit/Fabric APIs.", repo))
        break


def _mine_devops(root: Path, repo: str, out: list) -> None:
    df = _read(root / "Dockerfile")
    m = re.search(r"^FROM\s+(\S+)", df, re.M)
    if m:
        out.append(_entry("devops", f"{repo}: Docker base {m.group(1)}",
                          f"Dockerfile FROM {m.group(1)}. Pin digests for "
                          f"reproducible builds.", repo))
    wf = list((root / ".github" / "workflows").glob("*.yml")) + \
        list((root / ".github" / "workflows").glob("*.yaml"))
    if wf:
        out.append(_entry("devops", f"{repo}: GitHub Actions present ({len(wf)})",
                          "CI workflows exist — wire pipe SARIF upload for "
                          "inline findings.", repo))


def mine_repo(root: str | Path) -> list[dict[str, Any]]:
    """Все факты одного репозитория. Пусто на пустом — никогда не выдумывает."""
    base = Path(root)
    if not base.is_dir():
        return []
    repo = base.name
    out: list[dict[str, Any]] = []
    _mine_gradle(base, repo, out)
    _mine_maven(base, repo, out)
    _mine_node(base, repo, out)
    _mine_python(base, repo, out)
    _mine_minecraft(base, repo, out)
    _mine_devops(base, repo, out)
    seen = set()
    uniq = []
    for e in out:
        k = (e["domain"], e["title"])
        if k not in seen:
            seen.add(k)
            uniq.append(e)
    return uniq


def load_titles(path: Path) -> set[tuple[str, str]]:
    got = set()
    if not path.is_file():
        return got
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
            got.add((r.get("domain", ""), r.get("title", "")))
        except ValueError:
            pass
    return got
