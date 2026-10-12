# Tool Catalog (generated — do not edit by hand)

SOURCE_OF_TRUTH = registry (18 tools)

## code.review
- module: quality, backend: local, level: 0
- Static review: debt/dups/size

## forge.ping
- module: core, backend: local, level: 0
- Liveness probe

## knowledge.get_fact
- module: knowledge, backend: local, level: 0
- Single fact by id

## knowledge.search
- module: knowledge, backend: local, level: 0
- FTS over FORGE facts

## lab.build_plugin
- module: lab, backend: local, level: 2
- Clean build a plugin project

## lab.detect_build
- module: lab, backend: local, level: 0
- Detect gradle/maven/javac

## lab.run_unit_tests
- module: lab, backend: local, level: 2
- Gradle test suite with summary

## minecraft.analyze_logs
- module: minecraft, backend: local, level: 1
- lifecycle+errors for a plugin

## minecraft.check_compatibility
- module: minecraft, backend: local, level: 1
- api-version vs MC via Anvil

## minecraft.check_permissions
- module: minecraft, backend: local, level: 1
- permission checks vs declarations

## minecraft.validate_plugin_metadata
- module: minecraft, backend: local, level: 1
- plugin.yml lint via Anvil

## project.inspect
- module: project, backend: local, level: 0
- Languages, build files, MC versions, entry hints

## project.read_file
- module: project, backend: local, level: 0
- Read a file, workspace-confined, secrets scrubbed

## project.search
- module: project, backend: local, level: 0
- Regex search, workspace-confined, secrets scrubbed

## project.tree
- module: project, backend: local, level: 0
- Directory listing, workspace-confined

## ui.check_contrast
- module: ui, backend: local, level: 0
- Text/background contrast math

## ui.design_brief
- module: ui, backend: local, level: 0
- NL description -> brief+strategy

## ui.validate_layout
- module: ui, backend: local, level: 0
- Inventory slot/action/text checks
