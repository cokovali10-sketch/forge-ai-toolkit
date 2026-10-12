# Permissions

Levels (master spec, part VII):

- **0 — read**: tree, search, read_file, inspect, briefs, knowledge, review.
  No side effects. Always allowed.
- **1 — local reversible**: metadata lint, audits, log scans. Reads + safe
  local compute. Allowed by default.
- **2 — execute**: builds, test runs, server lifecycle, Anvil tools.
  Default ceiling (`allow_level=2`). Nothing above runs unless allowed.
- **3 — external**: downloads, webhooks, publishes, deploys.
  Denied unless explicitly allowed. Destructive ops need confirmation.
- **4 — sensitive**: production, secrets, mass deletion. Never granted
  implicitly; requires explicit opt-in per call.

Enforcement: `Registry.call(tool, params, allow_level=2)` checks the tool's
declared level BEFORE dispatch. Denied calls return
`status=DENIED` without executing anything. Disabling a module denies all
its tools the same way.

Timeouts: every local tool runs under its declared timeout (default 300s).
A timeout reports `status=TIMEOUT`; the worker thread is abandoned, not
killed (documented limitation — subprocess tools are killed properly).
