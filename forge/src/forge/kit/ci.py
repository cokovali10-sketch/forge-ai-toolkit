"""FORGE ci: генерация рабочего процесса GitHub Actions под стек проекта.

Читает файлы сборки и собирает `.github/workflows/forge.yml` с задачами под
каждую найденную экосистему (Python / Node / Go / Rust / Java). Файл не
перезаписывается без `force`, чтобы не затирать ручные правки.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

HEADER = """# Сгенерировано FORGE (forge ci). Правь смело — это обычный workflow.
name: forge
on:
  push:
    branches: [main, master]
  pull_request:
"""

JOB_TRIGGER = """
jobs:
"""

PY = """  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: install
        run: |
          python -m pip install --upgrade pip
          {install}
      - name: tests
        run: python -m pytest -q
"""

NODE = """  node:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - name: install
        run: npm ci || npm install
      - name: tests
        run: npm test --if-present
"""

GO = """  go:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: "stable"
      - name: build
        run: go build ./...
      - name: tests
        run: go test ./...
"""

RUST = """  rust:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - name: tests
        run: cargo test --all
"""

JAVA = """  java:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "21"
      - name: tests
        run: {cmd}
"""


def _py_install(base: Path) -> str:
    if (base / "requirements.txt").is_file():
        return "pip install -r requirements.txt"
    if (base / "pyproject.toml").is_file():
        return "pip install -e ."
    return "pip install pytest"


def detect_ecosystems(base: Path) -> list[str]:
    eco: list[str] = []
    if any((base / f).is_file() for f in
           ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt")):
        eco.append("python")
    if (base / "package.json").is_file():
        eco.append("node")
    if (base / "go.mod").is_file():
        eco.append("go")
    if (base / "Cargo.toml").is_file():
        eco.append("rust")
    if (base / "build.gradle").is_file() or (base / "build.gradle.kts").is_file():
        eco.append("gradle")
    elif (base / "pom.xml").is_file():
        eco.append("maven")
    return eco


def generate_ci(root: str | Path, force: bool = False) -> dict[str, Any]:
    """Пишет `.github/workflows/forge.yml`. Возвращает отчёт."""
    base = Path(root)
    if not base.is_dir():
        return {"ok": False, "error": f"не директория: {base}"}
    eco = detect_ecosystems(base)
    if not eco:
        return {"ok": False, "error": "стек не распознан (нет файлов сборки)"}
    wf = base / ".github" / "workflows" / "forge-ci.yml"
    if wf.exists() and not force:
        return {"ok": False, "exists": True, "path": str(wf),
                "error": "workflow уже существует (--force чтобы перезаписать)"}

    jobs: list[str] = []
    if "python" in eco:
        jobs.append(PY.format(install=_py_install(base)))
    if "node" in eco:
        jobs.append(NODE)
    if "go" in eco:
        jobs.append(GO)
    if "rust" in eco:
        jobs.append(RUST)
    if "gradle" in eco:
        cmd = "./gradlew test" if (base / "gradlew").is_file() else "gradle test"
        jobs.append(JAVA.format(cmd=cmd))
    elif "maven" in eco:
        jobs.append(JAVA.format(cmd="mvn -q test"))

    content = HEADER + JOB_TRIGGER + "\n".join(jobs)
    wf.parent.mkdir(parents=True, exist_ok=True)
    wf.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(wf), "ecosystems": eco,
            "jobs": len(jobs)}
