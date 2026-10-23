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
FORGE is the hands: **72 native tools + 120 Anvil tools + ~200 Hermes tools**
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
| `forge gen web/python-service/go-cli/node-api/rust-cli/paper` | project generators (landing, microservice, Go/Node/Rust, Paper plugin) |
| `forge fast write\|patch\|search\|context\|blueprint` | Speed: batch write/edit, one-pass search, context pack, blueprints |
| `forge web presets\|new\|audit\|preview` | Web Studio: 6 animated presets, 0..100 site audit, preview |
| `forge factory "<intent>"` | factory: intent → GUI plugin → javac → Purpur e2e → zip |
| `forge studio [--port 8100] [--open]` | multi-project browser workspace: audit, pipeline, generators |
| `forge make <kind> <name> [out]` | generator + conveyor check in one shot |
| `forge map <dir>` | project map: languages and LOC, entry points, import graph, deps |
| `forge test <dir>` | universal test runner (pytest/npm/go/cargo/gradle/maven/make) |
| `forge ci <dir>` | generate a GitHub Actions workflow for the detected stack |
| `forge secrets <dir>` | secret-leak scan (keys/tokens/passwords, masked output) |
| `forge deps <dir>` | dependency inventory + version hygiene (--check: outdated) |
| `forge doctor [dir]` | audit toolchains/versions and FORGE capabilities here |
| `forge audit <dir>` | one-shot project health (map/secrets/deps/quality) |
| `forge init [dir]` | onboard a project: CI + suppress stub, no overwrite |
| `forge report [dir]` | one consolidated report: audit + trend + pipe + env |
| `forge serve [dir]` | local dashboard + JSON API for the project |
| `forge baseline save\|check` | hold the line: fail only on NEW findings |
| `forge fix [dir]` | batch safe auto-fixes (backup, verify, rollback) |
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
cyclomatic complexity (>10), unused imports (dead code), `== None`/`!= True`
comparisons — and gives a concrete "extract / guard-clause /
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
if anything fails. `--only imports|constants|comparisons` picks a single kind of fix.
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

## The `kit` arsenal: `map`, `test`, `ci`, `secrets`, `deps`, `doctor`, `audit`, `init`

Eight commands that turn FORGE into a cannon for any project.

- `forge map <dir>` - instant map of unfamiliar code: languages and lines of
  code, build files, guessed entry points, largest files, the internal Python
  import graph, and external dependencies. Read-only, runs nothing. `--json`
  for agents.
- `forge test <dir>` - detects the stack (pytest / npm / go / cargo / gradle /
  maven / make) and runs the project's **native** tests. A missing toolchain is
  not a failure - it is an honest "skipped". `--detect` prints the chosen
  command.
- `forge ci <dir>` - reads build files and generates
  `.github/workflows/forge-ci.yml` with a job per ecosystem. Won't overwrite
  without `--force`.
- `forge secrets <dir>` - finds keys, tokens, private keys and passwords
  (AWS/GitHub/Google/Slack/Stripe/OpenAI, JWT, `password=...`). The full secret
  **never** reaches the output - only a mask. A line marked with
  `forge:allow-secret` is skipped.
- `forge deps <dir>` - dependency inventory across ecosystems
  (python/node/go/rust/java) plus hygiene: unbounded/loose versions,
  duplicates. `--check` also asks the native tools about outdated packages.
- `forge doctor [dir]` - audits the machine: which toolchains are present and
  their versions, and what FORGE can really do here. With a path it also
  reports the project's test stack. Read-only.
- `forge audit <dir>` - one command for overall project health: map, secret
  leaks, dependency hygiene and a code-quality score, combined into a 0..100
  score (the minimum over the "worst" area). `--deep` also runs the native
  tests, `--min-score N` is a CI gate.
- `forge init [dir]` - onboards a project in one command: creates the missing
  CI workflow and `.forge-suppress.json`, prints the next steps. Never
  overwrites without `--force` and never commits.

```bat
forge map .                       :: project map
forge test . --timeout 300        :: run the project's tests
forge ci .                        :: generate CI
forge secrets .                   :: check for leaks
forge deps . --check              :: deps and outdated
forge doctor .                    :: what is available, what to do
forge audit . --min-score 80      :: overall health + gate
forge init .                      :: connect the project to FORGE
```

For agents: `map.project`, `test.detect`, `test.run`, `ci.generate`,
`secrets.scan`, `deps.scan`, `doctor.check`, `audit.run`, `init.project`,
`report.full`.

## The single dashboard: `forge serve`

One screen for **any** project: health (audit), quality trend, dependencies,
secrets, conveyor history, arena scoreboard, environment — plus the same report
as a JSON API for agents and webhooks. Stdlib only, localhost only, read-only.

```bat
forge report .            :: the summary in the terminal (what the dashboard sees)
forge report . --json     :: the same summary, machine-readable
forge serve . --open      :: open the dashboard in a browser (port 8099)
forge serve . --watch 30  :: rebuild the report in the background every 30s
```

API: `GET /api/report[?deep=1]` — the full report; `GET /api/health` — score
and verdict. Agents get it in one call via `report.full`.

Export to a file: `forge report . --html report.html` — a standalone HTML page
(the same dashboard, data embedded; handy to attach to a PR).

## Studio: `forge studio`

`forge serve` shows **one** project. `forge studio` is a workspace for many:
a project registry (`.forge-studio.json`) on the left, tabs for Overview,
Pipeline, Quality, Generator and Reports on the right. Run the conveyor and see
each stage's status, generate a site or a Paper plugin with a live preview, and
download a standalone HTML report.

```bat
forge studio list                       :: what is already registered
forge studio add D:\work\my-project     :: add a project
forge studio --open --port 8100         :: open the studio
```

API: `GET /api/studio`, `GET /api/report`, `GET /api/pipeline/history`,
`POST /api/projects`, `POST /api/pipeline/run`, `POST /api/gen`, `/preview`.
Only `127.0.0.1`; only paths from the registry and `studio-workspace/` can be
read, generated into, or previewed; `..` escapes are rejected.

## Speed: `forge fast` (the Speed department)

The agent's bottleneck is rarely typing — it is the number of calls: one file
per call, one search per pattern, one read per file. `forge fast` removes that:

```bat
forge fast context --root . --query "class .*Service" --json
forge fast search --root . --pattern TODO --pattern FIXME
forge fast write --root . --spec files.json      :: many files, one transaction
forge fast patch --root . --spec edits.json      :: many edits, one transaction
forge fast blueprint --root D:\work\shop --template plugin-feature --name "Shop"
forge fast bench --root . --files 80             :: honest measurement here
```

| Tool | What it does |
|---|---|
| `speed.write` | many files in one call, atomic rollback, `base64`, `append`, `dry_run` |
| `speed.patch` | many exact/regex edits, `expected=N`, `all`, diff, atomic |
| `speed.search` | all patterns in one file pass, context lines, secrets scrubbed |
| `speed.context` | tree + selected files in one response, with a char/token budget |
| `speed.blueprint` | whole structure: `python-package`, `layered`, `http-service`, `plugin-feature`, `custom` |
| `speed.bench` | disk time and effective time with a simulated per-call round-trip |

Reference machine (80 files, 2 ms/call): write **3.60x**, atomic write
**2.11x**, batch patch **2.16x**, four searches in one pass **3.27x**. Batch
disk time can be higher — the win is removing round-trips; run
`forge fast bench` instead of trusting the table.

Rules: explicit `root`; `..`, drive roots, system directories and `.git` are
refused; edits are atomic by default; `atomic=false` only for a fresh generated
tree. Details: [docs/speed.md](./docs/speed.md).

## Web Studio: `forge web`

```bat
forge web presets                          :: aurora/neon/glass/brutalist/minimal/retro
forge web new "Aurora" --preset aurora --tagline "Sites that move"
forge web audit site --json                :: structure, WCAG contrast, JS, weight
forge web preview site --open              :: local preview
```

A site is just `index.html`, `styles.css`, `app.js` — no CDN, no dependencies:
reveal animations, tilt, magnet, cursor glow, counters, parallax, particles and
a `prefers-reduced-motion` guard. `forge gen web` uses the same engine and
accepts `--preset/--tagline/--lang`.

## Plugin factory: `forge factory`

```bat
forge factory "shop with a GUI and animations" --out D:\work
forge factory plan "player kits" --json
forge factory "auction" --no-e2e            :: build only, no server
```

Pipeline: `generate → validate → resourcepack (when asked) → build (javac
against paper-api) → e2e (real Purpur: boot, plugin load, command) → package
(zip)`. Each stage honestly reports `PASS/PARTIAL/FAIL/SKIPPED` with a reason;
overall `PASS` only when everything really ran. Output: `factory-report.json`,
`FACTORY.md`, `dist/<Name>-<version>-forge.zip`.

## Hold the line: `forge baseline`

On a large legacy codebase the audit immediately shows hundreds of findings, so
an honest `--min-score` gate is impossible to raise. `baseline` fixes that: a
snapshot of today's findings, then failing **only on new ones**. Fingerprints
are stable across line shifts.

```bat
forge baseline save .                       :: snapshot (.forge-baseline.json)
forge baseline check . --fail-on high       :: fail only on new high findings
forge baseline check . --fail-on medium --json
forge baseline diff .                       :: what is new / what got fixed
forge audit . --baseline                    :: audit + baseline gate
```

In CI: `forge baseline check . --fail-on high` — red only if you introduced a
**new** serious problem. For agents: `baseline.save`, `baseline.check`.

## Batch auto-fixes: `forge fix`

Runs **all** safe fixes across every `.py` in the project at once: unused
imports, repeated magic numbers, `== None` -> `is None`. Each file is fixed with
a backup and a syntax check; with `--test "cmd"` the tests run **once** at the
end, and on failure **all** changed files are rolled back — behaviour never
changes.

```bat
forge fix .                          :: all fixes across every .py
forge fix . --only imports           :: unused imports only
forge fix . --test "python -m pytest -q"   :: with a check and one big rollback
```

(Single file: `forge refactor file.py --apply`; a directory works too.)
For agents: `refactor.fix_dir`.

## The `pipe` conveyor in detail

8 stages: inspect → secrets → review → skills → knowledge → langs → clean-code
→ (optional `lab-e2e`
via `--heavy`). The `secrets` stage fails only on high-severity leaks
(keys/tokens/private keys); password heuristics are a warning. Fast stages run
in parallel (`--serial` restores the queue),
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

Now: core, conveyor (8 stages), lab, 5 languages, editor, generators (`web`,
`python-service`, `go-cli`, `node-api`, `rust-cli`, `paper`) + `make`, the
`map`/`test`/`ci`/`secrets`/`deps`/`doctor` arsenal, the `refactor` advisor, the
`do`/`loop`/`quality` autopilot, the `speed` department (batch files/edits,
context packs, blueprints), a first arena entry (reference 3/3), 233 green
tests.
Honestly not done: desktop app (needs Rust for Tauri - no cargo on this machine),
GUI screenshots, auto-client — marked `NOT_IMPLEMENTED`.
Next: PyPI release (metadata and workflow ready; needs your trusted publisher),
a real arena run by a model.

## License

MIT — see `forge/LICENSE`.

---

<div align="center">

**[🇷🇺 Читать на русском](./README_RU.md) · [🏠 Hub](./README.md)**

</div>

