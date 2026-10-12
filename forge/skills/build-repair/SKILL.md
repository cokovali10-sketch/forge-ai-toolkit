---
name: build-repair
version: 0.1.0
domain: build
activate-when:
  - any compilation, test, or packaging failure
  - after every file change that must be verified
verify-by:
  - full build green + tests green, twice if flake suspected
  - error text gone from fresh output (not just scrolled away)
limits:
  - max 5 fix cycles per issue, then stop and report
  - never present partial build as success
  - never rewrite working components to fix symptoms
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

## Knowledge sources
- knowledge base domain=build; compiler docs; prior fix log.

## Quality bar
- Fix is minimal, explained by the error text, verified by a clean rebuild.
