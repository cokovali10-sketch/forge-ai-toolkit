---
name: paper-plugin-expert
version: 0.1.0
domain: minecraft
activate-when:
  - task mentions Paper/Spigot/Purpur plugin, plugin.yml, Bukkit API
  - paper-plugin.yml or plugin.yml present
verify-by:
  - plugin_yml_lint + perm_audit + jar_inspect green
  - boot_check on a real server log (load + enable lines)
limits:
  - match server Java and api-version exactly; no invented API methods
  - no Bukkit API calls from async threads
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

## Knowledge sources
- knowledge base domain=minecraft; official Paper docs; Anvil mc_paper tools.

## Quality bar
- Audit pack passes; commands/config/permissions verified on a live log.
