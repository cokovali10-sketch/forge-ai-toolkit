---
name: speed-coder
version: 0.1.0
domain: productivity
activate-when:
  - a task needs more than 2 files created or edited
  - asked to scaffold a project, module, layer, service, or feature pack
  - asked to "do it faster", "batch it", "write a lot of code"
  - before reading many files to understand a codebase
verify-by:
  - `forge fast recipes` (MCP `speed.recipes`) lists the available blueprints
  - generated Python compiles (`python -m compileall`) and generated Java compiles with javac
  - after a batch change run `forge fast context --root <dir> --json` and inspect the touched files, then `forge pipe run <dir>` or the native tests
limits:
  - always pass an explicit `root`; writes outside it are rejected
  - never write inside `.git`; never overwrite user files without checking the plan
  - use `dry_run` first for risky patches and `force` only when the user asked for replacement
  - atomic batches roll back on failure; `atomic=false` is for fresh generated trees only
---

# Speed Coder

The bottleneck is usually **round-trips**, not typing. One call that writes 20
files is faster and safer than 20 calls that write one file each. FORGE Speed
exists for that.

## Choose the smallest tool

- **Understanding a repo:** `forge fast context --root DIR --query "regex"` or
  `--path src/pkg --path tests` returns one tree plus file contents, already
  secret-scrubbed. Do this before opening files one by one.
- **Finding many things:** `forge fast search --root DIR --pattern "A" --pattern "B"`
  scans every file once. Do not call search five times.
- **Creating a new structure:** `forge fast blueprint --root DIR --template T
  --name NAME`. Recipes: `python-package`, `layered`, `http-service`,
  `plugin-feature`, plus `custom` with a `files` map.
- **Writing a known set of files:** `forge fast write --root DIR --spec files.json`
  (one atomic transaction).
- **Editing many files:** `forge fast patch --root DIR --spec edits.json`
  (one transaction, unique-match by default, `all`/`regex`/`expected` available).

## Procedure

1. **Map first, once.** Run `speed.context` with the smallest useful `paths` or
   `query`. Read the returned `tree` and only the files you need.
2. **Pick a recipe or a spec.** For a new project use `speed.blueprint`; for an
   existing project use a `files` map. Never hand-write a tree when a recipe
   already matches.
3. **Preview risky changes.** `dry_run=true` returns `would_write` / `would_edit`
   and diffs without touching disk.
4. **Apply once.** Keep the whole change in one `speed.write` or `speed.patch`
   call. Unique matches protect you; `expected` catches refactors that moved.
5. **Verify immediately.** `forge fast context` the touched paths, then run the
   real build/tests (`forge pipe run`, `pytest`, `javac`, `npm test`).
6. **Measure when in doubt.** `forge fast bench --root DIR --files 80` prints
   disk time plus effective time with a simulated per-call round-trip.

## Spec shapes

```json
{"root": "D:/work/app", "files": {
  "src/app/__init__.py": "",
  "src/app/core.py": "def run(): ...\n"
}}
```

```json
{"root": "D:/work/app", "edits": [
  {"path": "src/app/core.py", "find": "def run(): ...", "replace": "def run() -> None:\n    ..."},
  {"path": "src/app/cli.py", "find": "old", "replace": "new", "all": true},
  {"path": "build.txt", "find": "1.0", "replace": "1.1", "regex": true, "expected": 1}
]}
```

## Quality bar

- The batch must be coherent: if one file imports another, create both in the
  same call so the tree is never half-written.
- Keep generated code runnable: Python `compileall`, Java `javac`, tests green.
- Do not trade safety for speed: default `atomic=true` for edits; use
  `atomic=false` only for a brand-new generated tree.
- Report what actually ran (build/test), not what should have run.
