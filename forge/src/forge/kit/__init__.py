"""FORGE kit: расширенный арсенал инструментов над проектом.

Модули:
- project_map: карта проекта — языки, строки кода, точки входа, граф импортов;
- test_runner: универсальный запуск тестов (pytest/go/npm/cargo/gradle/maven/make);
- ci: генерация рабочего процесса GitHub Actions под стек проекта;
- secrets: сканер секретов (ключи, токены, приватные ключи, пароли);
- doctor: аудит окружения (тулчейны/версии) и проекта.

Все функции принимают явный путь и работают только для чтения (кроме `ci`).
Используют: CLI (`forge map|test|ci|secrets|doctor`) и MCP (`map.*`, `test.*`,
`ci.*`, `secrets.*`, `doctor.*`).
"""
from __future__ import annotations

from forge.kit.audit import audit
from forge.kit.audit import render_text as render_audit
from forge.kit.baseline import check as baseline_check
from forge.kit.baseline import collect as baseline_collect
from forge.kit.baseline import diff as baseline_diff
from forge.kit.baseline import load as baseline_load
from forge.kit.baseline import render_text as render_baseline
from forge.kit.baseline import save as baseline_save
from forge.kit.ci import generate_ci
from forge.kit.deps import scan_deps
from forge.kit.doctor import doctor
from forge.kit.doctor import render_text as render_doctor
from forge.kit.init import init_project
from forge.kit.project_map import build_map, render_text
from forge.kit.report import full_report
from forge.kit.report import render_text as render_report
from forge.kit.secrets import scan_secrets
from forge.kit.test_runner import detect_test_command, run_tests

__all__ = [
    "build_map", "render_text", "detect_test_command", "run_tests",
    "generate_ci", "scan_secrets", "doctor", "render_doctor", "scan_deps",
    "audit", "render_audit", "init_project", "full_report", "render_report",
    "baseline_save", "baseline_check", "baseline_diff", "baseline_collect",
    "baseline_load", "render_baseline",
]
