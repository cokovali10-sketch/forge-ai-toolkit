"""Rust CLI generator: консольная утилита на stdlib, ноль зависимостей.

Generates: Cargo.toml, src/main.rs (функция greet + unit-тесты), README, .gitignore.
Проверяется: скобки Rust сходятся, Cargo.toml имеет [package].
"""
from __future__ import annotations

import re
from pathlib import Path

MAIN = '''use std::env;

pub fn greet(name: &str) -> String {
    let who = if name.trim().is_empty() { "world" } else { name.trim() };
    format!("hello {}", who)
}

fn main() {
    let name = env::args().nth(1).unwrap_or_default();
    println!("{}", greet(&name));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn greets_default() {
        assert_eq!(greet(""), "hello world");
    }

    #[test]
    fn greets_name() {
        assert_eq!(greet("Ada"), "hello Ada");
    }
}
'''


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]", "-", (name or "cli")).strip("-").lower()
    if not s or s[0].isdigit():
        s = "app-" + s if s else "app"
    return s


def generate(out_dir: str | Path, name: str = "cli") -> dict:
    """Generates a Rust CLI project. Returns {dir, files, ok, problems}."""
    safe = _slug(name)
    out = Path(out_dir)
    cargo = (f"[package]\nname = \"{safe}\"\nversion = \"0.1.0\"\n"
             f"edition = \"2021\"\n\n[dependencies]\n")
    files = {
        "Cargo.toml": cargo,
        "src/main.rs": MAIN,
        "README.md": f"# {safe}\n\n`cargo run -- Ada` — печатает приветствие.\n"
                     "`cargo test` — прогон тестов.\n",
        ".gitignore": "/target\n",
    }
    made = []
    for rel, content in files.items():
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        made.append(rel)
    problems = []
    rs = MAIN
    for ch_open, ch_close in (("{", "}"), ("(", ")")):
        if rs.count(ch_open) != rs.count(ch_close):
            problems.append(f"main.rs: {ch_open}{ch_close} не сходятся")
    if "[package]" not in cargo:
        problems.append("Cargo.toml: нет секции [package]")
    return {"dir": str(out), "files": made, "ok": not problems,
            "problems": problems}
