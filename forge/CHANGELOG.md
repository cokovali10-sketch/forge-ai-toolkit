# Changelog

## Unreleased
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
- 71 tests green; pipe passes on its own repo (SUCCESS, 4/4)

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
