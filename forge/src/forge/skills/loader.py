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

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Skill:
    name: str
    version: str
    domain: str
    title: str
    body: str
    path: str
    activates: list = field(default_factory=list)
    verifies: list = field(default_factory=list)
    limits: list = field(default_factory=list)


def _str(meta: dict, key: str, default: str = "") -> str:
    v = meta.get(key, default)
    return v if isinstance(v, str) else default


def _bullets(meta: dict, key: str) -> list[str]:
    v = meta.get(key, [])
    return list(v) if isinstance(v, list) else []


def parse_skill_file(path: str | Path) -> Skill:
    text = Path(path).read_text(encoding="utf-8")
    meta: dict[str, str | list[str]] = {}
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            cur: str | None = None
            for line in text[3:end].splitlines():
                m = re.match(r"^([A-Za-z-]+):\s*(.*)$", line)
                if m and (m.group(2).strip() or True):
                    k, v = m.group(1).strip(), m.group(2).strip()
                    cur = k
                    if v:
                        meta[cur] = v
                    elif cur not in meta:
                        meta[cur] = []
                    continue
                if line.strip().startswith("- ") and cur:
                    lst = meta.get(cur)
                    if not isinstance(lst, list):
                        lst = []
                        meta[cur] = lst
                    lst.append(line.strip()[2:].strip())
            body = text[end + 4 :].lstrip()
    title = ""
    for line in body.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    folder = Path(path).parent.name
    return Skill(
        name=_str(meta, "name", folder),
        version=_str(meta, "version", "0.1.0"),
        domain=_str(meta, "domain", "general"),
        title=title or folder,
        body=body,
        path=str(Path(path)),
        activates=_bullets(meta, "activate-when"),
        verifies=_bullets(meta, "verify-by"),
        limits=_bullets(meta, "limits"),
    )


def validate_skill(skill: Skill) -> list[str]:
    """Structure check per prompt section 7. Returns error list (empty = ok)."""
    errors = []
    if not skill.name or "/" in skill.name or " " in skill.name:
        errors.append("bad name (must be a single slug)")
    if not skill.version:
        errors.append("missing version")
    if not skill.domain:
        errors.append("missing domain")
    if not skill.title:
        errors.append("missing title (# heading)")
    if len(skill.body) < 200:
        errors.append("body too short (<200 chars): add procedure, examples, limits")
    if not skill.activates:
        errors.append("missing activate-when conditions")
    if not skill.verifies:
        errors.append("missing verify-by methods")
    if not skill.limits:
        errors.append("missing limits")
    for must in ("## ",):
        if must not in skill.body:
            errors.append("body has no ## sections (procedure/quality/sources expected)")
            break
    return errors


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
