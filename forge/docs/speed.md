# Speed Department

**Goal:** make the agent's *wall-clock* work shorter, not just the code shorter.
The bottleneck is usually the number of tool round-trips: one call per file, one
search per pattern, one read per file. Speed turns those into one call.

```
speed.write      many files, one transaction       (atomic rollback)
speed.patch      many edits, one transaction       (exact / regex / expected)
speed.search     many patterns, one file pass
speed.context    tree + selected file contents     (secret-scrubbed)
speed.blueprint  a whole complex structure         (recipes or custom)
speed.recipes    list recipes
speed.bench      measure the win on this machine
```

CLI: `forge fast <command>`. MCP module: `speed`. Module pack:
`module-packs/speed/module.json` (so `forge route` and `forge do` can pick it).

## Why one call wins

`forge fast bench --root . --files 80 --repeats 3` on the reference Windows
machine, with a conservative `2 ms` simulated round-trip per call:

| Operation | Sequential | One batch | Effective speedup |
|---|---:|---:|---:|
| write 80 files (fast path) | 45 ms disk + 160 ms calls | 55 ms disk + 2 ms | **3.60x** |
| write 80 files (atomic) | 45 ms disk + 160 ms calls | 95 ms disk + 2 ms | **2.11x** |
| patch 80 files | 56 ms disk + 160 ms calls | 98 ms disk + 2 ms | **2.16x** |
| search 4 patterns | 253 ms | 77 ms | **3.27x** |

Disk time can be *higher* for a batch (staging, rollback bookkeeping); the win
is eliminating N round-trips. Search is a straight single-pass win. Numbers are
hardware- and cache-dependent: repeated runs vary by roughly ±20%, and a real
LLM turn costs far more than 2 ms — raise it with `--overhead` to see your own
case. Always run the bench yourself instead of trusting the table.

The `write` fast path (`atomic=false`) is for fresh generated trees. Edits default
to `atomic=true`: old content is kept in memory and restored if any file fails.

## speed.write

```json
{"root": "D:/work/app", "files": {
  "src/app/__init__.py": "",
  "src/app/core.py": "def run() -> None:\n    ...\n",
  "assets/icon.png": {"base64": "iVBORw0KGgo..."}
}}
```

- `files` is a map or a list of `{path, content|base64, mode}`.
- `mode`: `write` (default), `create` (fail if exists), `append`.
- `atomic` default `true`; `backup` copies originals to `.forge-speed-backup/`.
- `dry_run` returns `would_write` without touching disk.
- `root` is explicit; `..`, drive roots, system directories and `.git` are refused.

## speed.patch

```json
{"root": "D:/work/app", "edits": [
  {"path": "src/app/core.py", "find": "def run():", "replace": "def execute():"},
  {"path": "src/app/cli.py", "find": "old", "replace": "new", "all": true},
  {"path": "build.txt", "find": "1\\.0", "replace": "1.1", "regex": true, "expected": 3}
]}
```

- Unique match by default; `all=true` for every occurrence.
- `expected=N` asserts the match count before writing (great for refactors).
- `regex`, `flags: "ims"`, `replace` backreferences.
- One file that fails aborts the whole transaction (`atomic=true`).
- `dry_run` returns unified diffs.

## speed.search

One walk, one read per file, all patterns checked per line.

```json
{"root": ".", "patterns": ["TODO", "FIXME", "class \\w+"],
 "globs": ["*.py"], "context": 2, "max_hits": 200}
```

- `regex` default `true`; `regex: false` for literal strings.
- `ignore_case`, `include_hidden`, `dir`, `context` lines.
- Results are grouped by pattern; secrets are scrubbed before returning.

## speed.context

The "read the repo once" call:

```json
{"root": "D:/work/app", "query": "class .*Service",
 "max_files": 20, "max_chars": 120000, "include_tree": true}
```

Returns an ASCII `tree`, selected `files` with `content`, `lang`, `lines`,
`truncated`, plus `total_chars` and `tokens_est`. Use `paths` for an explicit
slice (`src/pkg`, `tests/test_x.py`) or `query` to rank by hit count. Contents
are secret-scrubbed. This replaces ten `read_file` calls with one.

## speed.blueprint

Built-in recipes:

| key | language | structure |
|---|---|---|
| `python-package` | Python | src layout, model, service, CLI, unittest, pyproject |
| `layered` | Python | domain -> application -> infrastructure -> interfaces |
| `http-service` | Python | stdlib HTTP server, router, handlers, store, tests |
| `plugin-feature` | Java | Paper main, command, join listener, 27-slot GUI, service, YAML storage |
| `custom` | any | your `files` map with `{{name}}`, `{{module}}`, `{{class}}`, `{{package_path}}` |

```bash
forge fast blueprint --root D:/work/shop --template plugin-feature \
  --name "Shop Demo" --package com.forge.shop
```

`force=false` skips existing files and reports them. `dry_run=true` previews.
Generated Python is syntax-checked by the test suite; the Paper recipe compiles
with `javac` against the local `paper-api` + Adventure jars.

## Safety model

- Explicit `root`; every path is resolved and confined. Symlink escapes fail.
- No `.git` writes.
- `1000` files / `24 MB` per batch cap.
- Atomic batches roll back; a patch with any failed edit writes nothing.
- No network, no telemetry, no third-party dependencies.
- Secrets are scrubbed in search/context output.

## Plan for speed (what to do next)

1. **Use context first.** `speed.context` before reading; `speed.search` before
   grepping repeatedly.
2. **Batch every known change.** One `speed.write`/`speed.patch` per coherent
   change, not one call per file.
3. **Scaffold, don't hand-write.** Add a recipe when a structure repeats; keep
   recipes runnable and covered by compile tests.
4. **Measure before optimizing.** `speed.bench` reports disk and effective time
   separately; never claim a win without a number.
5. **Keep the safety default.** Atomic edits; fast path only for new trees.
6. **Next candidates:** batch rename/move (`speed.move`), incremental context
   cache keyed by file hashes, and parallel batch writes for >500 files. Add
   them only when a benchmark shows a real win.
