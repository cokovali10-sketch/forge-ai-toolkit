"""FORGE kit: расширенный арсенал инструментов над проектом.

Модули:
- project_map: карта проекта — языки, строки кода, точки входа, граф импортов;
- test_runner: универсальный запуск тестов (pytest/go/npm/cargo/gradle/maven/make);
- ci: генерация рабочего процесса GitHub Actions под стек проекта;
- secrets: сканер секретов (ключи, токены, приватные ключи, пароли).

Все функции принимают явный путь и работают только для чтения (кроме `ci`).
Используют: CLI (`forge map|test|ci|secrets`) и MCP (`map.*`, `test.*`, `ci.*`,
`secrets.*`).
"""
from __future__ import annotations

from forge.kit.ci import generate_ci
from forge.kit.project_map import build_map, render_text
from forge.kit.secrets import scan_secrets
from forge.kit.test_runner import detect_test_command, run_tests

__all__ = [
    "build_map", "render_text", "detect_test_command", "run_tests",
    "generate_ci", "scan_secrets",
]
