"""Project intelligence tools. Every call takes an explicit workspace root
and is confined by Sandbox. Schemas included for MCP exposure."""
from __future__ import annotations

from typing import Any

from ..security.sandbox import Sandbox

EXT_LANG = {
    ".java": "java", ".kt": "kotlin", ".py": "python", ".js": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".go": "go", ".rs": "rust",
    ".cs": "csharp", ".cpp": "cpp", ".c": "c", ".yml": "yaml", ".yaml": "yaml",
    ".json": "json", ".toml": "toml", ".gradle": "gradle", ".xml": "xml",
    ".md": "markdown", ".sql": "sql",
}


def _tree(p: dict[str, Any]) -> Any:
    sb = Sandbox(p["root"])
    return {"files": sb.walk(p.get("dir", "."), int(p.get("max_files", 2000)))}


def _search(p: dict[str, Any]) -> Any:
    sb = Sandbox(p["root"])
    return {"hits": sb.search(p["pattern"], p.get("dir", "."),
                             int(p.get("max_hits", 50)))}


def _read(p: dict[str, Any]) -> Any:
    sb = Sandbox(p["root"])
    return {"path": p["path"], "content": sb.read(p["path"], int(p.get("limit", 4000)))}


def _inspect(p: dict[str, Any]) -> Any:
    sb = Sandbox(p["root"])
    files = sb.walk(".", 5000)
    langs: dict[str, int] = {}
    for f in files:
        ext = "." + f.rsplit(".", 1)[-1].lower() if "." in f else ""
        lang = EXT_LANG.get(ext)
        if lang:
            langs[lang] = langs.get(lang, 0) + 1
    build = [f for f in ("build.gradle", "pom.xml", "package.json",
                         "pyproject.toml", "requirements.txt",
                         "settings.gradle", "gradlew", "gradlew.bat")
             if (sb.root / f).is_file()]
    mc = _mc_version(sb)
    entry = [f for f in files if f.endswith(
        ("plugin.yml", "paper-plugin.yml", "fabric.mod.json", "Main.java",
         "main.py", "__main__.py", "index.ts", "App.tsx"))][:10]
    return {"languages": langs, "build_files": build,
            "minecraft": mc, "entry_hints": entry, "file_count": len(files)}


def _mc_version(sb: Sandbox) -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        import re
        gp = sb.root / "gradle.properties"
        if gp.is_file():
            txt = gp.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"minecraft_version\s*=\s*(\S+)", txt)
            if m:
                out["minecraft"] = m.group(1)
            m = re.search(r"loader_version\s*=\s*(\S+)", txt)
            if m:
                out["loader"] = m.group(1)
        for name in ("plugin.yml", "paper-plugin.yml"):
            fp = sb.root / "src" / "main" / "resources" / name
            if fp.is_file():
                txt = fp.read_text(encoding="utf-8", errors="replace")
                m = re.search(r"api-version\s*:\s*['\"]?([\w.]+)", txt)
                if m:
                    out["bukkit_api"] = m.group(1)
                break
    except OSError:
        pass
    return out


TOOLS = [
    ("project.tree", "Directory listing, workspace-confined",
     {"root": "workspace root (required)", "dir": "subdir, default .",
      "max_files": "cap, default 2000"}, _tree),
    ("project.search", "Regex search, workspace-confined, secrets scrubbed",
     {"root": "workspace root (required)", "pattern": "regex (required)",
      "dir": "subdir, default .", "max_hits": "cap, default 50"}, _search),
    ("project.read_file", "Read a file, workspace-confined, secrets scrubbed",
     {"root": "workspace root (required)", "path": "relative path (required)",
      "limit": "chars, default 4000"}, _read),
    ("project.inspect", "Languages, build files, MC versions, entry hints",
     {"root": "workspace root (required)"}, _inspect),
]
