# FORGE Architecture

```
agent/CLI/MCP-client
        │  JSON-RPC (stdio) / CLI / python import
        ▼
┌───────────────────────────────┐
│ Registry (core/registry.py)   │  modules + tool_owner routing
│  backends: local │ anvil │ hermes (http)
└───────┬───────────┬───────────┘
        │           │
        ▼           ▼
 project/ lab/ ui/ bench/   knowledge/   skills/   quality/   speed/
(sandboxed) (server) (PIL)  (SQLite FTS) (SKILL.md) (review)  (batch I/O)
        │           │
        ▼           ▼
  Anvil (subprocess)   Hermes (http, optional)
```

## Key decisions

- **Thin glue, real tools.** FORGE never duplicates Anvil/Hermes; it routes,
  validates and reports. New capability = new backend or module, core untouched.
- **Honesty by construction.** Unavailable integrations return structured
  errors (Ollama/Hermes down, no Node, no Mineflayer) — never faked results.
- **Sandbox first.** Every file op resolves inside an explicit workspace root;
  secrets scrubbed; `..` escapes raise.
- **Evidence before claims.** Benchmarks discriminate good/bad fixtures;
  lab runs prove on real servers; MCP proven vs official SDK 2.3.0.
- **Bounded repair.** checkpoint → check → bundle → rollback; the agent edits,
  the mechanism guarantees safety. Max attempts and timeouts everywhere.
- **Deterministic UI work.** Briefs/strategies/validators are keyword- and
  math-driven (no model needed); screenshots are declared out of scope until
  a client harness exists.
- **Fewer round-trips, same guarantees.** The `speed` department batches writes,
  edits, searches and context reads into one call each; atomic batches roll
  back, paths stay confined, and `speed.bench` reports disk and effective time
  separately instead of claiming a win.

## Data flow (typical task)

`forge route "Paper plugin GUI"` → manifests ranked → skills loaded →
knowledge searched → project inspected → code generated → lab builds →
server boots → scenarios assert → report.md → commit.
