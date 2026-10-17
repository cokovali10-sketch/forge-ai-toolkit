"""FORGE test: универсальный запуск тестов проекта.

Определяет стек по файлам сборки и запускает родную команду тестов:
Python (pytest), Node (npm test), Go (go test), Rust (cargo test),
Gradle, Maven, Make. Нет тулчейна — это WARNING, а не провал
(чужой компьютер не виноват). Всё через timeout, ничего не устанавливает.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _has(root: Path, *names: str) -> bool:
    return any((root / n).is_file() for n in names)


def _npm_test(root: Path) -> bool:
    pkg = root / "package.json"
    if not pkg.is_file():
        return False
    try:
        data = json.loads(pkg.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return False
    return isinstance(data.get("scripts"), dict) and "test" in data["scripts"]


def _make_has_test(root: Path) -> bool:
    mk = root / "Makefile"
    if not mk.is_file():
        return False
    try:
        for line in mk.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
            if line.startswith("test:") or line.startswith("test "):
                return True
    except OSError:
        return False
    return False


def detect_test_command(root: str | Path) -> dict[str, Any] | None:
    """Подбирает команду тестов по стеку. None — тестов/стека не видно."""
    base = Path(root)
    if _has(base, "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
            "Pipfile", "tox.ini"):
        return {"kind": "python", "command": [sys.executable, "-m", "pytest", "-q"],
                "why": "Python-проект (pytest)"}
    if _npm_test(base):
        return {"kind": "node", "command": ["npm", "test"],
                "why": "package.json со скриптом test"}
    if _has(base, "go.mod"):
        return {"kind": "go", "command": ["go", "test", "./..."],
                "why": "Go-модуль (go.mod)"}
    if _has(base, "Cargo.toml"):
        return {"kind": "rust", "command": ["cargo", "test"],
                "why": "Rust-пакет (Cargo.toml)"}
    if _has(base, "build.gradle", "build.gradle.kts"):
        gradlew = "./gradlew" if (base / "gradlew").is_file() else "gradle"
        return {"kind": "gradle", "command": [gradlew, "test"],
                "why": "Gradle-проект"}
    if _has(base, "pom.xml"):
        return {"kind": "maven", "command": ["mvn", "-q", "test"],
                "why": "Maven-проект"}
    if _make_has_test(base):
        return {"kind": "make", "command": ["make", "test"],
                "why": "Makefile с целью test"}
    return None


def run_tests(root: str | Path, timeout: int = 600) -> dict[str, Any]:
    """Запускает тесты проекта. Возвращает структурный отчёт."""
    base = Path(root)
    if not base.is_dir():
        return {"ok": False, "ran": False, "error": f"не директория: {base}"}
    detected = detect_test_command(base)
    if not detected:
        return {"ok": True, "ran": False,
                "reason": "тесты не обнаружены (нет стека/скрипта test)"}
    cmd = list(detected["command"])
    exe = cmd[0]
    if exe.startswith("./"):
        if not (base / exe[2:]).is_file():
            return {"ok": True, "ran": False, "kind": detected["kind"],
                    "reason": f"нет тулчейна ({exe}) — тесты пропущены"}
    elif exe != sys.executable and not shutil.which(exe):
        return {"ok": True, "ran": False, "kind": detected["kind"],
                "reason": f"нет тулчейна ({exe}) — тесты пропущены"}
    try:
        r = subprocess.run(cmd, cwd=str(base), capture_output=True, text=True,
                           timeout=timeout)
    except FileNotFoundError:
        return {"ok": True, "ran": False, "kind": detected["kind"],
                "reason": f"нет тулчейна ({exe}) — тесты пропущены"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "ran": True, "kind": detected["kind"],
                "command": cmd, "timeout": True,
                "reason": f"тесты не уложились в {timeout}s"}
    log = (r.stdout or "") + (r.stderr or "")
    return {"ok": r.returncode == 0, "ran": True, "kind": detected["kind"],
            "command": cmd, "returncode": r.returncode,
            "summary": _summarize(log), "log_tail": log[-2000:]}


def _summarize(log: str) -> str:
    """Ищет в выводе строку-итог (passed/failed/ok)."""
    import re
    for line in reversed(log.splitlines()):
        s = line.strip()
        if re.search(r"\b\d+\s+(passed|failed|error)", s) or \
           re.search(r"^(ok|FAIL|PASS)\b", s) or "test result:" in s:
            return s[:200]
    return ""
