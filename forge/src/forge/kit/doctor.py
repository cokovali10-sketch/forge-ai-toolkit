"""FORGE doctor: аудит окружения и возможностей.

Отвечает на два вопроса честно и быстро:
1. Что есть на этой машине (тулчейны и версии) и что FORGE здесь реально может.
2. (если дан путь) — что за проект и чем его проверять.

Только чтение: ни один тулчейн не запускается иначе как с `--version`
(или `-version` для Java). Ничего не меняет.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# (id, команда-проверка, что означает)
TOOLS: list[tuple[str, list[str], str]] = [
    ("git", ["--version"], "версии, страховочные точки, rollback"),
    ("python", [], "FORGE ядро, python-service, pytest"),
    ("pytest", ["--version"], "python-тесты"),
    ("node", ["--version"], "node-api, npm-проекты"),
    ("npm", ["--version"], "node-тесты/сборка"),
    ("go", ["version"], "go-cli, go-тесты"),
    ("cargo", ["--version"], "rust-cli, cargo-тесты"),
    ("rustc", ["--version"], "компиляция Rust"),
    ("java", ["-version"], "Paper-плагины, Java-тесты"),
    ("javac", ["-version"], "компиляция Java"),
    ("gradle", ["--version"], "gradle-проекты"),
    ("mvn", ["-version"], "maven-проекты"),
    ("make", ["--version"], "make-цели"),
    ("docker", ["--version"], "lab-фикстуры в контейнерах"),
    ("gh", ["--version"], "GitHub из терминала"),
]

_GENERATORS = ["web", "python-service", "go-cli", "node-api", "rust-cli",
               "paper"]


def _run_version(exe: str, args: list[str], timeout: float = 10.0) -> str:
    try:
        r = subprocess.run([exe, *args], capture_output=True, text=True,
                           timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    text = (r.stdout or "") + "\n" + (r.stderr or "")
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:120]
    return ""


def _check(name: str, args: list[str]) -> dict[str, Any]:
    if name == "python":
        return {"name": "python", "present": True,
                "version": sys.version.split()[0],
                "path": sys.executable}
    exe = shutil.which(name)
    if not exe:
        return {"name": name, "present": False, "version": ""}
    return {"name": name, "present": True,
            "version": _run_version(exe, args) or "present", "path": exe}


def doctor(root: str | Path | None = None) -> dict[str, Any]:
    """Аудит машины (+ проекта, если дан путь). Ничего не меняет."""
    tools = []
    for name, args, _why in TOOLS:
        info = _check(name, args)
        info["why"] = _why
        tools.append(info)

    try:
        from forge.langs import LANGS
        langs = sorted(LANGS)
    except Exception:  # pragma: no cover - defensive
        langs = []
    try:
        from forge.pipe.stages import DEFAULT_STAGES, HEAVY_STAGES
        n_stages = len(DEFAULT_STAGES) + len(HEAVY_STAGES)
    except Exception:  # pragma: no cover - defensive
        n_stages = 0

    out: dict[str, Any] = {
        "ok": True,
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "tools": tools,
        "present": sorted(t["name"] for t in tools if t["present"]),
        "missing": sorted(t["name"] for t in tools if not t["present"]),
        "capabilities": {"languages": langs, "stages": n_stages,
                         "generators": list(_GENERATORS)},
    }

    if root is not None:
        from forge.kit.test_runner import detect_test_command
        base = Path(root)
        out["project"] = {"root": str(base), "exists": base.is_dir()}
        if base.is_dir():
            cmd = detect_test_command(base)
            out["project"]["test_command"] = cmd
    return out


def render_text(report: dict[str, Any]) -> str:
    lines = ["FORGE doctor", "=" * 40,
             f"python {report.get('python')}  platform {report.get('platform')}",
             "", "Тулчейны:"]
    for t in report.get("tools", []):
        mark = "+" if t["present"] else "-"
        ver = t["version"] or "-"
        lines.append(f"  [{mark}] {t['name']:<8} {ver}")
    cap = report.get("capabilities", {})
    lines.append("")
    lines.append("Языки: " + ", ".join(cap.get("languages", [])))
    lines.append("Стадий конвейера: " + str(cap.get("stages", 0)))
    lines.append("Генераторы: " + ", ".join(cap.get("generators", [])))
    proj = report.get("project")
    if proj:
        lines.append("")
        cmd = proj.get("test_command")
        if cmd:
            lines.append(f"Проект {proj['root']}: тесты -> {cmd['command']}")
        else:
            lines.append(f"Проект {proj['root']}: стек тестов не распознан")
    return "\n".join(lines)
