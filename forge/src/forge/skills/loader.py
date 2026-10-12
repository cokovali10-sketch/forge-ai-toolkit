"""Skill loader. A skill is a folder with SKILL.md:

---
name: java-expert
version: 0.1.0
domain: java
---
# title
body...
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Skill:
    name: str
    version: str
    domain: str
    title: str
    body: str
    path: str


def parse_skill_file(path: str | Path) -> Skill:
    text = Path(path).read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            body = text[end + 4 :].lstrip()
    title = ""
    for line in body.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    folder = Path(path).parent.name
    return Skill(
        name=meta.get("name", folder),
        version=meta.get("version", "0.1.0"),
        domain=meta.get("domain", "general"),
        title=title or folder,
        body=body,
        path=str(Path(path)),
    )


def load_skills(skills_dir: str | Path) -> dict[str, Skill]:
    out: dict[str, Skill] = {}
    base = Path(skills_dir)
    if not base.is_dir():
        return out
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        f = child / "SKILL.md"
        if f.is_file():
            try:
                skill = parse_skill_file(f)
                out[skill.name] = skill
            except OSError:
                continue
    return out
