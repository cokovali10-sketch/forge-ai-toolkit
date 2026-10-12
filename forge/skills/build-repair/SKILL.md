---
name: build-repair
version: 0.1.0
domain: build
---
# Build-Repair Loop

The only loop allowed: reproduce -> read the FULL error -> fix root cause ->
rebuild -> rerun tests -> verify.

## Rules
- Read compiler output completely; the first error is usually the only real one.
- Distinguish code errors from environment flakes (locked files, daemons,
  network). Rerun once before changing code.
- Never declare victory on a partial build (`compileJava` green is not `build`
  green; `build` green is not `test` green).
- Keep fixes minimal and reversible; commit after green, not before.
- Bisect ruthlessly: empty entrypoint -> minimal init -> pieces, until the
  failing piece is isolated. Guessing is forbidden; experiments are cheap.
- Log every fix with the exact error text so the knowledge base grows.
