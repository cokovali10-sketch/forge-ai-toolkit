# Changelog

## Unreleased
- gen: web landing, python-service, go-cli (each self-validated, CLI+MCP),
  paper stays as the small Minecraft workshop
- make: `forge make <kind> <name>` = generator + conveyor check in one shot
  (CLI + MCP `make.project`)
- refactor: clean-code advisor (`forge refactor`, MCP `refactor.inspect`) —
  long functions, deep nesting, duplicate blocks, magic numbers, too many args,
  God-classes; structure-only, never changes behavior
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
