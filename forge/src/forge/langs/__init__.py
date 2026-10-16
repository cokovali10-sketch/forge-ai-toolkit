"""FORGE language modules: one expert per language.

python | javascript | rust | cpp | go — каждый: detect/lint/test/scaffold.
Импортируй реестр, а не модули напрямую: `from forge.langs import LANGS`.
"""
from forge.langs import cpp, go, javascript, python, rust

LANGS = {
    "python": python,
    "javascript": javascript,
    "rust": rust,
    "cpp": cpp,
    "go": go,
}

__all__ = ["LANGS", "python", "javascript", "rust", "cpp", "go"]
