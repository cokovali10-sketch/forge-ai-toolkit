---
name: paper-plugin-expert
version: 0.1.0
domain: minecraft
---
# Paper Plugin Expert

## Scaffold
- `plugin.yml` (or paper-plugin.yml): name, version, main, api-version.
  Quote colons in YAML, no tabs, UTF-8 without BOM.
- Java 21 for 1.21.x servers; match server's Java exactly.

## Lifecycle
- onEnable/onDisable must be fast and failure-proof; disable cleanly on error.
- Config defaults via saveDefaultConfig; never crash on missing keys.

## API safety
- Scheduler: never touch Bukkit API async; use runTask for world access.
- Persist player data on quit + periodic save, not only on disable.
- MiniMessage: balance tags, escape user input, no legacy color mix.

## Checks before ship
- plugin_yml_lint, perm_audit (checks vs declarations), jar_inspect,
  api-version vs target MC, boot_check on a real log.
