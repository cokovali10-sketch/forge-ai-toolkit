# FORGE Testing Lab

Isolated Paper/Purpur plugin verification: build, unit tests, real server
boot, console commands, log diagnostics, cleanup. Client/GUI automation
is declared NOT_IMPLEMENTED (no Mineflayer/Node here) — never faked.

## Quick proof (takes ~1 min, needs Java 21)

```bat
D:\Forge-Factority\.venv\Scripts\python -m forge.cli lab e2e
```

What it does: compiles `tests/fixture-plugin` (LabPing) against paper-api,
creates an isolated env, boots Purpur 1.21.11, asserts `LabPing enabled`,
runs `/labping hello` and asserts `labpong hello`, stops the server,
destroys the env, writes `lab-runs/<id>/artifacts/report.md`.

Verified 2026-10-12: 9/9 PASS in 44s (Purpur 1.21.11, Temurin 21).

## Layout

- `src/forge/lab/env.py` — profiles, create/install/destroy
- `src/forge/lab/build.py` — detect gradle/maven, clean build, javac fixture
- `src/forge/lab/unittests.py` — gradle/pytest runners with parsed summaries
- `src/forge/lab/server.py` — subprocess console: start/wait/command/stop/logs
- `src/forge/lab/scenarios.py` — PASS/FAIL/ERROR/SKIPPED records with repro
- `src/forge/lab/report.py` — markdown run reports
- `src/forge/lab/runner.py` — end-to-end orchestration
- `src/forge/lab/tools.py` — MCP tool surface (client/GUI = NOT_IMPLEMENTED)
- `tests/fixture-plugin/` — LabPing fixture (command + plugin.yml)
- `lab-servers/` — purpur jar + paper-api/adventure/bungee jars (NOT in git)

## Server jars

- `lab-servers/purpur-1.21.11.jar` — from api.purpurmc.org (bootstrapper)
- `lab-servers/api/` — paper-api + adventure + examination + bungee-chat
  (compile classpath; versions pinned in this doc)

## Limits (honest)

- No automated game client (Mineflayer needs Node — absent).
- No visual GUI verification (no screenshot harness in lab yet).
- MockBukkit not wired; mock tests are not claimed as server proof.
- One server at a time per env; resource caps via profile (xmx/timeout).
