"""FORGE deps: инвентарь зависимостей и гигиена по всем экосистемам.

Разбирает манифесты (requirements, pyproject, package.json, go.mod, Cargo.toml,
pom.xml, build.gradle) и выдаёт:
- полный список объявленных зависимостей (с версиями) по экосистемам;
- findings по гигиене: неограниченные/слишком свободные версии, дубликаты.

По умолчанию — офлайн (только чтение файлов). `--check` дополнительно
запускает родные проверки устаревшего (pip/npm/go/cargo), если они есть и
разрешена сеть; отсутствие тулчейна — не провал.

Только чтение и никаких сетевых вызовов, если не запрошен `check=True`.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

MANIFESTS = ["requirements.txt", "requirements-dev.txt", "pyproject.toml",
             "package.json", "go.mod", "Cargo.toml", "pom.xml",
             "build.gradle", "build.gradle.kts"]

_SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist",
              "build", "target", "out", ".gradle", ".mypy_cache"}


def _dep(name: str, spec: str, eco: str, file: str, dev: bool = False) -> dict:
    return {"name": name.strip(), "spec": (spec or "").strip(),
            "ecosystem": eco, "file": file, "dev": dev}


def _parse_requirements(text: str, file: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith(("-r", "-e", "--", "git+", "http")):
            continue
        m = re.match(r"^([A-Za-z0-9_.\-]+)\s*(?:\[[^\]]*\])?\s*([<>=!~].*)?$",
                     line)
        if m:
            out.append(_dep(m.group(1), m.group(2) or "", "python", file))
    return out


def _spec_dep(spec: str, file: str) -> dict | None:
    m = re.match(r"^([A-Za-z0-9_.\-]+)\s*(?:\[[^\]]*\])?\s*([<>=!~].*)?$", spec)
    if not m:
        return None
    return _dep(m.group(1), m.group(2) or "", "python", file)


def _parse_pyproject(text: str, file: str) -> list[dict]:
    out: list[dict] = []
    try:
        import tomllib
        data = tomllib.loads(text)
    except Exception:
        data = None
    if isinstance(data, dict):
        project = data.get("project") or {}
        for spec in project.get("dependencies") or []:
            d = _spec_dep(str(spec), file)
            if d:
                out.append(d)
        for specs in (project.get("optional-dependencies") or {}).values():
            for spec in specs or []:
                d = _spec_dep(str(spec), file)
                if d:
                    out.append(_dep(d["name"], d["spec"], "python", file, dev=True))
        poetry = (data.get("tool") or {}).get("poetry") or {}
        for name, val in (poetry.get("dependencies") or {}).items():
            if name.lower() == "python":
                continue
            if isinstance(val, str):
                out.append(_dep(name, val, "python", file))
            elif isinstance(val, dict):
                out.append(_dep(name, str(val.get("version", "")), "python", file))
        return out
    # fallback: только блок dependencies = [ ... ]
    for m in re.finditer(r"dependencies\s*=\s*\[(.*?)\]", text, re.S):
        for spec in re.findall(r"[\"']([^\"']+)[\"']", m.group(1)):
            d = _spec_dep(spec, file)
            if d:
                out.append(d)
    return out


def _parse_package_json(text: str, file: str) -> list[dict]:
    try:
        data = json.loads(text)
    except ValueError:
        return []
    out = []
    for key, dev in (("dependencies", False), ("devDependencies", True)):
        for name, spec in (data.get(key) or {}).items():
            out.append(_dep(name, str(spec), "node", file, dev))
    return out


def _parse_go_mod(text: str, file: str) -> list[dict]:
    out = []
    in_req = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("require ("):
            in_req = True
            continue
        if in_req and s == ")":
            in_req = False
            continue
        if s.startswith("require "):
            s = s[len("require "):].strip()
            in_req = True  # одиночная строка: разберём ниже и закроем
        if in_req and s and not s.startswith("//"):
            parts = s.split("\t") if "\t" in s else s.split()
            if len(parts) >= 2:
                out.append(_dep(parts[0], parts[1], "go", file))
            if line.strip().startswith("require "):
                in_req = False
    return out


def _parse_cargo_toml(text: str, file: str) -> list[dict]:
    out = []
    section = ""
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("[") and s.endswith("]"):
            section = s.strip("[]").strip()
            continue
        if section in ("dependencies", "dev-dependencies",
                       "build-dependencies"):
            m = re.match(r"^([A-Za-z0-9_.\-]+)\s*=\s*(.+)$", s)
            if not m:
                continue
            name, val = m.group(1), m.group(2)
            spec = ""
            q = re.match(r"^[\"']([^\"']+)[\"']", val)
            if q:
                spec = q.group(1)
            else:
                vm = re.search(r"version\s*=\s*[\"']([^\"']+)[\"']", val)
                spec = vm.group(1) if vm else ""
            out.append(_dep(name, spec, "rust", file,
                            dev=section != "dependencies"))
    return out


def _parse_pom(text: str, file: str) -> list[dict]:
    out = []
    for block in re.findall(r"<dependency>(.*?)</dependency>", text, re.S):
        a = re.search(r"<artifactId>([^<]+)</artifactId>", block)
        v = re.search(r"<version>([^<]+)</version>", block)
        g = re.search(r"<groupId>([^<]+)</groupId>", block)
        if a:
            name = f"{g.group(1)}:{a.group(1)}" if g else a.group(1)
            out.append(_dep(name, v.group(1) if v else "", "java", file))
    return out


def _parse_gradle(text: str, file: str) -> list[dict]:
    out = []
    for m in re.finditer(
            r"(?:implementation|api|testImplementation|compileOnly|"
            r"runtimeOnly)\s*[\(\s]['\"]([^:'\"]+):([^:'\"]+):([^'\"]+)['\"]",
            text):
        out.append(_dep(f"{m.group(1)}:{m.group(2)}", m.group(3),
                        "java", file))
    return out


_PARSERS = {
    "requirements.txt": _parse_requirements,
    "pyproject.toml": _parse_pyproject,
    "package.json": _parse_package_json,
    "go.mod": _parse_go_mod,
    "Cargo.toml": _parse_cargo_toml,
    "pom.xml": _parse_pom,
    "build.gradle": _parse_gradle,
    "build.gradle.kts": _parse_gradle,
}


def _find_manifests(root: Path) -> list[Path]:
    found: list[Path] = []
    for dirpath, dirnames, filenames in __import__("os").walk(
            root, onerror=lambda e: None):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            if fn in _PARSERS or re.match(r"^requirements.*\.txt$", fn):
                found.append(Path(dirpath) / fn)
        if len(found) > 200:
            break
    return found


def _hygiene(deps: list[dict]) -> list[dict]:
    out = []
    seen: dict[tuple, str] = {}
    for d in deps:
        spec = d["spec"]
        if d["ecosystem"] == "node" and spec in ("*", "latest", ""):
            out.append({"kind": "wildcard-version", "severity": "medium",
                        "detail": f"{d['name']} = {spec or '*'}",
                        "file": d["file"]})
        elif d["ecosystem"] in ("python", "rust") and not spec:
            out.append({"kind": "unpinned", "severity": "medium",
                        "detail": f"{d['name']} без версии", "file": d["file"]})
        elif spec and (spec[0] in "^~" or spec.startswith(">=")):
            out.append({"kind": "loose-range", "severity": "low",
                        "detail": f"{d['name']} {spec}", "file": d["file"]})
        key = (d["ecosystem"], d["name"])
        if key in seen and seen[key] != d["file"]:
            out.append({"kind": "duplicate", "severity": "low",
                        "detail": f"{d['name']} объявлен в {seen[key]} и {d['file']}",
                        "file": d["file"]})
        else:
            seen.setdefault(key, d["file"])
    return out


def _native_outdated(root: Path, ecos: set[str],
                     timeout: float = 60.0) -> dict[str, Any]:
    """Best-effort: родные проверки устаревшего. Сеть/тулчейн могут быть недоступны."""
    result: dict[str, Any] = {}
    checks = [
        ("python", "pip", ["list", "--outdated", "--format=json"]),
        ("node", "npm", ["outdated", "--json"]),
        ("go", "go", ["list", "-u", "-m", "all"]),
    ]
    for eco, tool, args in checks:
        if eco not in ecos:
            continue
        exe = shutil.which(tool)
        if not exe:
            result[eco] = {"ok": False, "reason": f"{tool} не найден"}
            continue
        try:
            r = subprocess.run([exe, *args], capture_output=True, text=True,
                               cwd=str(root), timeout=timeout)
            result[eco] = {"ok": True, "output": (r.stdout or "")[:4000]}
        except (OSError, subprocess.TimeoutExpired) as e:
            result[eco] = {"ok": False, "reason": f"{type(e).__name__}: {e}"}
    return result


def scan_deps(root: str | Path, check: bool = False,
              timeout: float = 60.0) -> dict[str, Any]:
    """Инвентарь зависимостей проекта + гигиена. check=True — ещё и устаревшее."""
    base = Path(root)
    if not base.is_dir():
        return {"ok": False, "error": f"не директория: {base}"}
    deps: list[dict] = []
    files: list[str] = []
    for manifest in _find_manifests(base):
        try:
            text = manifest.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        parser = _PARSERS.get(manifest.name)
        if parser is None:  # requirements-*.txt
            parser = _parse_requirements
        rel = str(manifest.relative_to(base)).replace("\\", "/")
        got = parser(text, rel)
        if got:
            files.append(rel)
            deps.extend(got)

    by_eco: dict[str, int] = {}
    for d in deps:
        by_eco[d["ecosystem"]] = by_eco.get(d["ecosystem"], 0) + 1

    out: dict[str, Any] = {
        "ok": True, "root": str(base), "count": len(deps),
        "by_ecosystem": by_eco, "manifests": files,
        "dependencies": deps,
        "findings": _hygiene(deps),
    }
    if check:
        out["outdated"] = _native_outdated(base, set(by_eco), timeout)
    return out
