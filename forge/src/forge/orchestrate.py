"""FORGE do: оркестратор «намерение -> план -> проверка».

Одна команда собирает всё, что нужно для задачи, в понятный план:
- какие модули подходят (route по манифестам),
- какие скиллы применимы (по совпадению слов),
- что говорит база знаний,
- если просят создать проект — какой цех (generator) и команда,
- как проверить результат (pipe/loop).

`--run` дополнительно прогоняет замкнутый контур `loop` и возвращает вердикт.
FORGE не «додумывает» работу за агента: он выдаёт исполнимый план и честную
проверку, а решение и правки остаются за мозгом.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

GENERATORS: dict[str, list[str]] = {
    "web": ["лендинг", "landing", "сайт", "site", "website", "страниц", "web"],
    "python-service": ["сервис", "service", "api", "микросервис", "microservice",
                       "бэкенд", "backend"],
    "go-cli": ["cli", "утилита", "утилит", "инструмент командной",
               "tool", "command-line"],
    "paper": ["плагин", "plugin", "paper", "minecraft", "майнкрафт", "spigot",
              "bukkit"],
}


def _tokens(text: str) -> set[str]:
    import re
    return {t for t in re.split(r"[^\wа-яё]+", text.lower()) if len(t) > 2}


def _route_modules(intent: str, forge_root: str) -> list[dict[str, Any]]:
    try:
        from forge.modules.manifest import load_packs, route
        packs = load_packs(Path(forge_root) / "module-packs")
        return [{"module": mid, "why": reasons}
                for mid, reasons in route(intent, packs)]
    except Exception:  # noqa: BLE001
        return []


def _match_skills(intent: str, forge_root: str) -> list[dict[str, Any]]:
    try:
        from forge.skills.loader import load_skills
        skills = load_skills(Path(forge_root) / "skills")
    except Exception:  # noqa: BLE001
        return []
    want = _tokens(intent)
    scored: list[tuple[int, dict[str, Any]]] = []
    for s in skills.values():
        hay = _tokens(" ".join([s.name, s.domain, s.title, " ".join(s.activates)]))
        score = len(want & hay)
        if s.domain and s.domain in intent.lower():
            score += 2
        if score:
            scored.append((score, {"skill": s.name, "domain": s.domain,
                                   "title": s.title}))
    scored.sort(key=lambda kv: -kv[0])
    return [d for _, d in scored[:3]]


def _knowledge(intent: str, forge_root: str) -> list[dict[str, Any]]:
    try:
        from forge.knowledge.store import KnowledgeStore
        store = KnowledgeStore(":memory:")
        kdir = Path(forge_root) / "knowledge"
        loaded = 0
        if kdir.is_dir():
            for jf in sorted(kdir.glob("*.jsonl")):
                loaded += store.load_jsonl(jf)
        if not loaded:
            return []
        return [{"title": h.get("title"), "domain": h.get("domain")}
                for h in store.search(intent, limit=3)]
    except Exception:  # noqa: BLE001
        return []


def _detect_generator(intent: str) -> str:
    low = intent.lower()
    best = ""
    best_hits = 0
    for kind, words in GENERATORS.items():
        hits = sum(1 for w in words if w in low)
        if hits > best_hits:
            best, best_hits = kind, hits
    return best


def plan(intent: str, root: str, forge_root: str,
         name: str = "demo") -> dict[str, Any]:
    """Строит исполнимый план по намерению."""
    modules = _route_modules(intent, forge_root)
    skills = _match_skills(intent, forge_root)
    knowledge = _knowledge(intent, forge_root)
    kind = _detect_generator(intent)
    steps: list[dict[str, Any]] = []
    if kind:
        steps.append({"step": "generate",
                      "command": f"forge make {kind} {name} --out \"{root}\"",
                      "why": f"намерение указывает на цех «{kind}»"})
    steps.append({"step": "inspect", "command": f"forge inspect \"{root}\"",
                  "why": "понять структуру, языки и сборку"})
    if modules:
        steps.append({"step": "use-modules",
                      "command": "forge modules",
                      "why": "подходящие эксперты: "
                             + ", ".join(m["module"] for m in modules)})
    if skills:
        steps.append({"step": "follow-skills",
                      "command": "forge skills list",
                      "why": "процедуры: " + ", ".join(s["skill"] for s in skills)})
    steps.append({"step": "verify", "command": f"forge pipe run \"{root}\"",
                  "why": "проверить результат конвейером"})
    steps.append({"step": "auto-fix", "command": f"forge loop \"{root}\"",
                  "why": "довести до зелёного автоматически"})
    return {"intent": intent, "root": root, "generator": kind,
            "modules": modules, "skills": skills, "knowledge": knowledge,
            "steps": steps}


def run(intent: str, root: str, forge_root: str, name: str = "demo",
        execute: bool = False, max_attempts: int = 3) -> dict[str, Any]:
    """Строит план; при execute=True дополнительно прогоняет loop."""
    out = plan(intent, root, forge_root, name=name)
    if execute:
        from forge.pipe.loop import run_loop
        out["verify"] = run_loop(root, forge_root, max_attempts=max_attempts)
    return out
