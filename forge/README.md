# FORGE Core (MVP)

Universal AI Capability Enhancement Framework — thin layer over real tools
(Anvil/Hermes), portable Skills, SQLite knowledge base, MCP server.

## Layout (grows into module-packs/, tests/benchmarks/, apps/desktop/)

- `src/forge/core/` — module registry + tool protocol
- `src/forge/skills/` — skill loader (SKILL.md)
- `src/forge/knowledge/` — SQLite FTS store
- `src/forge/mcp/` — stdio MCP server (tools/list, tools/call)
- `src/forge/cli/` — CLI
- `skills/` — portable skill packs
- `knowledge/seed.jsonl` — first facts
- `tests/` — pytest (unit now, benchmarks/ later)

## Run

```bat
cd forge
python -m pytest tests -q
python -m forge.cli modules
python -m forge.cli skill java-expert
python -m forge.mcp.server
```

## Status

Phase 0/1: registry + skills + knowledge + MCP skeleton + tests green.
Desktop (Tauri) deferred: no Node in env.
