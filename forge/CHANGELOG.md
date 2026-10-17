# Changelog

## Unreleased
- kit: `forge baseline save|check|diff` (`baseline.save`/`baseline.check`) —
  "hold the line": snapshot current findings, then fail only on NEW ones
  (fingerprints stable across line shifts); `forge audit --baseline` gates too
- serve: `forge report --html FILE` — a standalone offline dashboard page
- serve: `forge serve [dir] [--port] [--open] [--watch]` — a single local
  read-only dashboard (health, quality trend, deps, secrets, pipe history,
  arena, environment) + JSON API (`/api/report`, `/api/health`); stdlib only
- kit: `forge report [dir]` and MCP `report.full` — one consolidated report
  (audit + quality trend + pipe history + arena + environment) shared by the
  CLI, the MCP server and the dashboard
- kit: `forge init [dir]` (`init.project`) — onboards a project in one command:
  writes the missing CI workflow and `.forge-suppress.json`, prints next steps;
  never overwrites without `--force`
- kit: `forge audit <dir>` (`audit.run`) — one-shot project health: composes the
  project map, secret scan, dependency hygiene and the code-quality score into a
  single 0..100 score (min over the worst area); `--deep` also runs the native
  tests, `--min-score N` is a CI gate
- do: `forge do "<intent>"` suggests an `audit` step first when the intent is
  about reviewing/auditing (проверь/аудит/утечки/зависимости/health)
- test: secret fixtures in the test suite carry the `forge:allow-secret` marker
  on the very line the scanner reads, so FORGE's own audit reports 0 leaks
- kit: `forge doctor [dir]` (`doctor.check`) — audits the machine: which
  toolchains exist and their versions, what FORGE can really do here; with a
  path it also reports the project's test stack (read-only)
- kit: `forge deps <dir>` (`deps.scan`) — dependency inventory across
  python/node/go/rust/java plus hygiene findings (wildcard/unpinned/loose
  versions, duplicates); `--check` asks native tools about outdated packages
- pipe: new stage `secrets` (now 8 stages) — the conveyor fails only on
  high-severity leaks (keys/tokens/private keys), password heuristics warn;
  a line marked `forge:allow-secret` is skipped
- bench: first arena entries — a synthetic reference candidate scores 3/3 and
  a bad one 0/3; the harness now resolves javac sources to absolute paths and
  falls back to `javac` from PATH when `FORGE_JAVAC` is unset; the rendered
  board uses ASCII markers (cp1251-safe)
- packaging: PyPI metadata (classifiers, authors, project URLs, keywords),
  version 0.12.0, and a `release` GitHub Actions workflow (build + trusted
  publishing on `v*` tags)
- kit: new `forge/kit` arsenal, four commands (CLI + MCP):
  - `map` (`map.project`) — project map: languages and LOC, build files,
    entry points, largest files, internal Python import graph, dependencies
  - `test` (`test.detect` / `test.run`) — universal runner for
    pytest/npm/go/cargo/gradle/maven/make; a missing toolchain is "skipped",
    not a failure
  - `ci` (`ci.generate`) — writes `.github/workflows/forge-ci.yml` with a job
    per ecosystem; won't overwrite without `--force`
  - `secrets` (`secrets.scan`) — leaks of AWS/GitHub/Google/Slack/Stripe/OpenAI
    keys, JWTs, private keys and `password=` assignments; output is masked
    (the full secret never appears)
- gen: two new generators — `node-api` (zero-dependency Node HTTP API with
  `node --test` tests) and `rust-cli` (zero-dependency Cargo CLI with unit
  tests); both wired into `make`, CLI `gen`, MCP and the `do` router
- refactor: new safe auto-fix — PEP8 comparisons (`== None`/`!= True` …) are
  rewritten to `is` / `is not`; detected as `simplifiable-comparison`,
  applied via `--apply` or `--only comparisons`
- refactor: Python files are read as `utf-8-sig`, so sources saved with a UTF-8
  BOM (common on Windows editors) are analyzed and fixed instead of failing to
  parse
- do: skill routing no longer false-matches on generic words — a generic token
  like `api` (from "Bukkit API") used to pull an unrelated Minecraft skill into
  a REST-API intent; now `forge do` requires an explicit domain hit or several
  real matches, understands Russian domain synonyms, and lightly prefers skills
  that fit the detected generator
- refactor: dead-code detection — unused imports (Python) as a finding, with a
  safe auto-fix (`--apply`) that removes them only when truly unreferenced
  (skips `# noqa`, star and multi-line imports, honours `__all__`/strings)
- refactor: `--apply --only imports|constants` picks a single kind of fix
- fix: magic-constant auto-fix sliced UTF-8 `col_offset` as characters, which
  corrupted lines with non-ASCII (Cyrillic) text; now byte-accurate
- review: debt-marker scan no longer matches TODO/FIXME inside string literals
  or docstrings (FORGE's own rule definitions used to flag themselves)
- loop: safety checkpoint is now non-destructive — `forge loop` no longer hides
  uncommitted work in a `git stash` (it records HEAD and leaves your tree intact)
- loop: `forge loop <dir>` closes the conveyor into a self-healing loop —
  safety checkpoint -> pipe -> repair bundles -> safe fixes (or `--on-fail`
  hook) -> retry up to N attempts; `SUCCESS` only when truly green
  (CLI + MCP `loop.run`)
- do: `forge do "<intent>"` orchestrator — routes generator / modules / skills
  / knowledge into an executable plan; `--run` verifies immediately
  (CLI + MCP `do.plan` / `do.run`)
- quality: `forge quality <dir>` dashboard — health score, issues by kind,
  languages, recorded history + trend, and a CI gate (`--min-score`,
  `--max-regression`) (CLI + MCP `quality.report`)
- gen: web landing, python-service, go-cli (each self-validated, CLI+MCP),
  paper stays as the small Minecraft workshop
- make: `forge make <kind> <name>` = generator + conveyor check in one shot
  (CLI + MCP `make.project`)
- refactor: clean-code advisor (`forge refactor`, MCP `refactor.inspect`) —
  long functions, deep nesting, duplicate blocks, magic numbers, too many args,
  God-classes; structure-only, never changes behavior
- refactor: cyclomatic complexity (>10 flagged) + project health score 0..100
  (severity-weighted, normalized per file)
- refactor: `--plan` (prioritized steps), `--sarif` (GitHub code scanning),
  multi-language heuristic analyzer (JS/TS/Go/C++/Java/Kotlin/Rust)
- refactor: `--apply` safe auto-fix — repeated magic numbers -> named constants
  with backup, syntax check, optional tests and automatic rollback
  (CLI + MCP `refactor.plan`/`refactor.sarif`/`refactor.apply`)
- window: "Чистый код" tab with health score and refactor plan
- pipe: new advisory stage `clean-code` (6/7, allow_fail) surfaces a refactor
  plan each run; skill `refactor-expert` gives agents the safe recipe
- docs: conveyor is now 7 stages (clean-code before lab-e2e)
- evolve: Self-Update detector (stale skills/rules/history/toolchains),
  `forge evolve` CLI + `evolve.check` MCP
- edit: universal object editor (JSON engine + YAML via Anvil, lite-schemas,
  dry-run, .forge-bak, rollback), CLI + `edit.*` MCP tools
- langs: python/javascript/rust/cpp/go modules (detect/lint/test/scaffold),
  `forge lang` CLI, `5/6` pipe stage, `lang.*` MCP tools
- review: 4MB cap, `# forge-ignore` line suppressions, `--changed` hold-the-line

## 0.11.0
- pipe: conveyor `forge pipe run` (headless JSON + exit codes + checkpoints/resume)
  and `forge pipe window` (tkinter, dark theme, stage details, preload)
- quality.review: `.forge-suppress.json` suppressions (reason required, visible in report)
- pipe as MCP tools (`pipe.stages`/`pipe.run`/`pipe.status`), `--only` stages,
  run history (`.forge-pipe-history.jsonl`), window «Продолжить» button
- pipe watch mode: auto re-run on file change (stdlib watcher, own artifacts
  excluded), CLI `forge pipe watch` + «👁 Следить» toggle in window
- pipe fingerprints: content-hash per stage, repeat runs use checkpoint cache
  (only affected stages re-run), `(кэш)` marks in output
- pipe heavy stage `lab-e2e` (real Purpur boot, env-gated, `--heavy` only)
- pipe parallel fast stages (`--serial` restores queue), heavy always last
  and only on green fast; fixed as_completed eating timeouts (deadlines)
- window history tab, run timer, stage titles, SKIPPED icon
- pipe heal (checkpoint + run + repair bundles + suggested modules)
- pipe SARIF output, `pipe init-ci` (CI workflow + badge), repo gets real CI
- stage plugins (`.forge-stages/`), `pipe all` multi-project with `--clean`
- VS Code extension scaffold, `forge-core` 0.11.0 packаged (sdist+wheel verified)
- knowledge base 6 -> 47 entries (java/paper/gradle/testing/python/git/security)
- window: no focus stealing (topmost removed), bigger geometry, selected-tab style
- cache correctness: suppress file in review fingerprint, cached FAIL counts
- live proof: full --heavy run green incl. real 63s Purpur boot
- 81 tests green; pipe passes on its own repo (SUCCESS, 5/5)
- hardening: walk limits + onerror, history rotation (200), safe report writes,
  --no-plugins, corrupt-data tolerance, backup failure paths, secrets untouched
- arena: `bench arena` records runs, `bench board` renders public scoreboard
  (latest-per-agent, raw jsonl kept); miner is manual-only by policy
- hub: `pipe hub` web dashboard (read-only, auto-refresh, JSON API)
- vscode extension packaged (forge-pipe-0.1.0.vsix, syntax verified with node)

## 0.10.0
- MCP: minecraft.* (metadata/permissions/compat/logs via Anvil), knowledge.*,
  code.review (static: debt/dups/size); `forge config init`
- Config wired into CLI groundwork

## 0.9.0
- forge.toml config system with validation
- fix-loop: checkpoint/diff/rollback/cycle + CLI
- UI iterate (contrast-scored opacity) + external graphics import
- 41 tests

## 0.8.0
- Benchmark harness: 5 check types, 3 tasks, good/bad discrimination proven

## 0.7.0
- Paper plugin generator (validated inputs)
- Live proof: generated ClanCore compiled + 8/8 on Purpur
- MCP compat proven vs official SDK 2.3.0

## 0.6.0
- MCP compatibility test vs official SDK client

## 0.5.0
- AAA Interface Engine: briefs (RU/EN), strategies A-D, design systems,
  component validators, PIL asset packs, MythicShop demo (8/8 e2e)

## 0.4.0
- Testing Lab: env/build/server/scenarios/reports; Purpur e2e 9/9

## 0.3.0
- Unified CLI (tools/call), Anvil+Hermes modules, router, sandbox

## 0.2.0
- Skills validation, manifests, project tools, Ollama adapter

## 0.1.0
- Core MVP: registry, Anvil bridge, skills, FTS knowledge, MCP server, CLI
