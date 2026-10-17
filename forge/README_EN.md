<div align="center">

# ◆ FORGE AI Toolkit

**[🇷🇺 Читать на русском](./README_RU.md) · [🏠 Hub](./README.md)**

*A tool for general development of any projects in any languages:
check conveyor, MCP server, language experts, object editor,
knowledge base — plus a testing lab for Minecraft. No model training,
no paid APIs, no hallucinated results — only verifiable tools.*

</div>

---

## Contents

1. [What and why](#what-and-why)
2. [Install (human, 5 minutes)](#install-human-5-minutes)
3. [Quick start: 5 commands](#quick-start-5-commands)
4. [Connecting an AI agent (MCP)](#connecting-an-ai-agent-mcp)
5. [Instructions for AI agents](#instructions-for-ai-agents)
6. [Command reference](#command-reference)
7. [The `refactor` advisor (clean code)](#the-refactor-advisor-clean-code)
8. [Autopilot: `do`, `loop`, `quality`](#autopilot-do-loop-quality)
9. [The `pipe` conveyor in detail](#the-pipe-conveyor-in-detail)
10. [Safety](#safety)
11. [FAQ](#faq)
12. [Status and roadmap](#status-and-roadmap)

---

## What and why

A regular AI agent can reason but has no hands: it cannot build a project,
run tests against a real server, or check 500 files in a second.
FORGE is the hands: **32 native tools + 120 Anvil tools + ~200 Hermes tools**
behind one CLI and one MCP server.

Two modes of the same conveyor:
- **Human** — a window with buttons, graphs and history (`pipe window`)
- **AI** — the same checks without a window: JSON + exit codes (`pipe run`)

## Install (human, 5 minutes)

Requirements: Windows 10/11, Python 3.10+ (verified on 3.12), Git.
Everything runs offline except model/package downloads.

```bat
git clone https://github.com/cokovali10-sketch/forge-ai-toolkit.git
cd forge-ai-toolkit
python -m venv .venv
.venv\Scripts\python -m pip install -e forge
.venv\Scripts\python -m pytest forge\tests -q
```

Done when tests are green. Next — see the arsenal:

```bat
.venv\Scripts\python -m forge.cli modules
.venv\Scripts\python -m forge.cli pipe run <your-project>
```

## Quick start: 5 commands

```bat
:: 1. What project is in front of you
.venv\Scripts\python -m forge.cli inspect D:/my-project

:: 2. Full conveyor: inspect -> review -> skills -> knowledge -> langs -> clean-code
.venv\Scripts\python -m forge.cli pipe run D:/my-project

:: 3. Same, but with a window, buttons and history
.venv\Scripts\python -m forge.cli pipe window D:/my-project

:: 4. Build a plugin and run it on a real server
.venv\Scripts\python -m forge.cli lab e2e

:: 5. Ask the knowledge base
.venv\Scripts\python -m forge.cli know "gradle wrapper"
.venv\Scripts\python -m forge.cli know mine D:/my-project --apply
```

## Connecting an AI agent (MCP)

FORGE is an MCP server over stdio (verified against the official SDK client).
Config for Claude Desktop / any MCP client (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "forge": {
      "command": "D:/Forge-Factority/.venv/Scripts/python.exe",
      "args": ["-m", "forge.cli", "mcp"],
      "cwd": "D:/Forge-Factority"
    }
  }
}
```

Permission levels 0–4 (`docs/permissions.md`): reading — 0, toolchains — 1,
builds and writes — 2. The client decides what the agent may do.

## Instructions for AI agents

> If you are an AI agent reading this: how to work with FORGE.

1. **Start with inspect, not with reading everything:**
   `project.inspect {"root": "<dir>"}` or `forge inspect <dir>` — structure,
   languages, build. Don't load the whole project into context.
2. **Verify with the conveyor, not with your eyes:** `pipe.run {"root": "<dir>"}`
   returns a report `{status, stages[]}`. `FAILED` + `bundles` from `pipe.heal`
   is your repair plan: stage, error, files, suggested modules.
3. **Search knowledge, don't invent:** `know "<query>"` / `knowledge.search`.
   No answer — say so honestly, never invent APIs (especially Java/Minecraft versions).
4. **Write through skills:** `skills list` → pick one (`paper-plugin-expert`,
   `java-expert`, `build-repair`...) → follow the skill procedure.
5. **Builds must be real:** `lab.build_plugin`, `lab.run_unit_tests`,
   `lab e2e`. MockBukkit is not a real server — say so in your report.
6. **Don't lie:** `NOT_IMPLEMENTED` is a valid answer. Call unfinished things
   unfinished and guesses guesses (see the `quality` engine levels).
7. **Don't touch user files without `heal`:** checkpoint before changes,
   rollback (`fix rollback`) after failure. Never delete uncommitted work.

## Command reference

| Command | What it does |
|---|---|
| `forge modules` / `skills list` / `route "..."` | arsenal, skills, module routing per task |
| `forge inspect <dir>` | project structure |
| `forge pipe run/watch/window/heal/all` | conveyor: once / watch / window / heal / everything |
| `forge pipe init-ci / --sarif` | CI workflow + SARIF for GitHub |
| `forge lab e2e / detect` | lab: real server / build detection |
| `forge bench list/run/arena/board` | benchmarks and the public scoreboard |
| `forge lang detect/lint/test/scaffold` | 5 language experts (python/js/rust/cpp/go) |
| `forge edit inspect/get/set/validate/rollback` | object editor (native JSON, YAML via Anvil) |
| `forge evolve` | what is stale and who should fix it |
| `forge gen web/python-service/go-cli/paper` | project generators (landing, microservice, Go CLI, Paper plugin) |
| `forge make <kind> <name> [out]` | generator + conveyor check in one shot |
| `forge refactor <file\|dir>` | clean-code advisor: long functions, nesting, duplicates, magic numbers |
| `forge do "<intent>"` | orchestrator: generator, modules, skills, knowledge, plan, verify |
| `forge loop <dir>` | closed loop: conveyor → repair bundles → safe fixes → retry |
| `forge quality <dir>` | quality dashboard + trend + regression gate for CI |
| `forge know ... / know mine` | knowledge base + miner (manual only!) |
| `forge ui brief/pack` | design briefs and resource packs |
| `forge fix rollback` | roll back to the checkpoint |
| `forge docs` | regenerate tool catalogs |

## The `refactor` advisor (clean code)

`forge refactor <file|dir>` finds what makes code hard to read — long
functions (>50 lines), deep nesting (>3), duplicated blocks (3+ lines), magic
numbers, functions with too many args, God-classes (>200 lines), high
cyclomatic complexity (>10), unused imports (dead code) — and gives a concrete
"extract / guard-clause /
named constant" suggestion for each, plus a **health score 0..100**. It only
recommends structure, never changes behavior. Python is parsed via AST;
JS/TS, Go, C++, Java, Kotlin and Rust via a brace-based heuristic.

```bat
forge refactor src --plan                  :: prioritized: what to fix first
forge refactor src --sarif out.sarif       :: GitHub code scanning
forge refactor app.py --apply --test "pytest -q"
```

`--apply` extracts repeated magic numbers into named constants and removes dead
imports — with a backup, a syntax check, your tests, and **automatic rollback**
if anything fails. `--only imports|constants` picks a single kind of fix.
For agents: `refactor.inspect`, `refactor.plan`, `refactor.sarif`,
`refactor.apply`. Skill: `refactor-expert`.

## Autopilot: `do`, `loop`, `quality`

Three commands that close the conveyor into a loop.

- `forge do "<intent>"` — the orchestrator. Parses the intent, picks a
  generator (`web`, `python-service`, `go-cli`, `paper`), modules, skills and
  knowledge, and emits an executable plan: what to generate, inspect and
  verify. With `--run` it also verifies immediately.
- `forge loop <dir>` — repairs itself. Takes a safety checkpoint, runs the
  conveyor; if red, builds repair bundles, applies safe fixes (or your
  `--on-fail "command"`) and retries up to `--attempts` (default 3). Returns
  `SUCCESS` only when truly green.
- `forge quality <dir>` — one screen of truth: health score, issues by kind,
  languages, trend over recorded snapshots and a gate. `--min-score 80` fails
  CI when quality drops below; `--max-regression 2` fails on a drop of more
  than 2 points.

```bat
forge do "build a landing page for a coffee shop" --root .
forge do "fix the project" --root . --run
forge loop . --attempts 3
forge quality . --min-score 80 --max-regression 2
```

For agents: `do.plan`, `do.run`, `loop.run`, `quality.report`.

## The `pipe` conveyor in detail

7 stages: inspect → review → skills → knowledge → langs → clean-code →
(optional `lab-e2e`
via `--heavy`). Fast stages run in parallel (`--serial` restores the queue),
the heavy one strictly after and only on green. Repeat runs reuse the
checkpoint cache by content hashes. `--changed` checks only git-changed files
(hold-the-line). `--only` runs selected stages. Noise suppressions require a
reason (`.forge-suppress.json`), line-level via `# forge-ignore`.

## Safety

- Read-only over foreign projects with limits (30,000 files, files >4MB skipped),
  no symlink following, access errors ignored
- Writes only own artifacts; history rotated (200); plugins only from
  `.forge-stages/`, `--no-plugins` disables fully
- `heal` checkpoints first (git-stash or copy up to 200MB) with rollback
- The miner and watchers **never enable themselves** — only on your command.
  Secrets are never read (miner takes manifests only)

## FAQ

**Is this a replacement for my agent?** No. It's its hands. The brain is your model.
**Does it work offline?** Yes, except model/package downloads.
**Is Windows required?** Primary platform is Windows; the core is pure Python, portable.
**Where is the window?** `pipe window` (tkinter from the Python box). AI uses `pipe run`.
**Found a bug?** Format: command → expected → got → log. Issue templates in the repo.

## Status and roadmap

Now: core, conveyor, lab, 5 languages, editor, generators + `make`, the
`refactor` advisor, the `do`/`loop`/`quality` autopilot, 140 green tests.
Honestly not done: desktop app (needs Node for Tauri), GUI screenshots,
auto-client — marked `NOT_IMPLEMENTED`.
Next: project generators (web/Python/Go), first arena entry, PyPI release.

## License

MIT — see `forge/LICENSE`.

---

<div align="center">

**[🇷🇺 Читать на русском](./README_RU.md) · [🏠 Hub](./README.md)**

</div>
