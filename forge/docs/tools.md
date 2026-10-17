# Tool Catalog (generated — do not edit by hand)

SOURCE_OF_TRUTH = registry (59 tools)

## audit.run
- module: kit, backend: local, level: 1
- One-shot project health: map/secrets/deps/quality (+tests)

## baseline.check
- module: kit, backend: local, level: 1
- Fail only on NEW findings vs the saved baseline

## baseline.save
- module: kit, backend: local, level: 1
- Snapshot current findings to .forge-baseline.json

## ci.generate
- module: kit, backend: local, level: 1
- Generate a GitHub Actions workflow for the project stack

## code.review
- module: quality, backend: local, level: 0
- Static review: debt/dups/size

## deps.scan
- module: kit, backend: local, level: 0
- Dependency inventory + hygiene for all ecosystems

## do.plan
- module: loop, backend: local, level: 0
- Turn an intent into an executable plan

## do.run
- module: loop, backend: local, level: 2
- Plan + verify intent via the loop

## doctor.check
- module: kit, backend: local, level: 0
- Audit toolchains/versions and FORGE capabilities

## edit.get
- module: edit, backend: local, level: 0
- Get value by dotted path

## edit.inspect
- module: edit, backend: local, level: 0
- Show document structure

## edit.rollback
- module: edit, backend: local, level: 2
- Restore .forge-bak

## edit.set
- module: edit, backend: local, level: 2
- Set value (backup + optional schema)

## edit.validate
- module: edit, backend: local, level: 0
- Validate against lite-schema

## evolve.check
- module: evolve, backend: local, level: 0
- Find stale skills/rules/history

## forge.ping
- module: core, backend: local, level: 0
- Liveness probe

## gen.go_cli
- module: gen, backend: local, level: 1
- Scaffold Go CLI tool

## gen.node_api
- module: gen, backend: local, level: 1
- Scaffold Node HTTP API (zero deps)

## gen.paper
- module: gen, backend: local, level: 1
- Scaffold Paper plugin

## gen.python_service
- module: gen, backend: local, level: 1
- Scaffold stdlib microservice

## gen.rust_cli
- module: gen, backend: local, level: 1
- Scaffold Rust CLI tool (zero deps)

## gen.web
- module: gen, backend: local, level: 1
- Scaffold landing page

## init.project
- module: kit, backend: local, level: 1
- Bootstrap FORGE into a project (CI + suppress stub)

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

## lang.detect_all
- module: langs, backend: local, level: 0
- Detect languages in a dir

## lang.lint
- module: langs, backend: local, level: 1
- Syntax-check a language in a dir

## lang.scaffold
- module: langs, backend: local, level: 1
- Scaffold minimal project

## lang.test
- module: langs, backend: local, level: 1
- Run a language test suite

## loop.run
- module: loop, backend: local, level: 2
- Run pipe and self-heal up to N attempts

## make.project
- module: make, backend: local, level: 2
- Scaffold + verify project

## map.project
- module: kit, backend: local, level: 0
- Project map: languages, LOC, entries, imports

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

## pipe.heal
- module: pipe, backend: local, level: 2
- Checkpoint + run + repair bundles

## pipe.run
- module: pipe, backend: local, level: 2
- Run conveyor headless, returns report

## pipe.stages
- module: pipe, backend: local, level: 0
- List conveyor stages

## pipe.status
- module: pipe, backend: local, level: 0
- Checkpoint + history tail

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

## quality.report
- module: quality, backend: local, level: 0
- Quality snapshot + trend

## refactor.apply
- module: refactor, backend: local, level: 2
- Apply safe auto-fixes (backup+verify+rollback)

## refactor.inspect
- module: refactor, backend: local, level: 0
- Find clean-code problems in a file/dir

## refactor.plan
- module: refactor, backend: local, level: 0
- Prioritized refactor plan for a file/dir

## refactor.sarif
- module: refactor, backend: local, level: 0
- Clean-code findings as SARIF 2.1.0

## report.full
- module: kit, backend: local, level: 1
- One consolidated report: audit+quality trend+pipe+arena

## secrets.scan
- module: kit, backend: local, level: 0
- Scan for leaked secrets (masked output)

## test.detect
- module: kit, backend: local, level: 0
- Detect the project's native test command

## test.run
- module: kit, backend: local, level: 1
- Run the project's native test suite

## ui.check_contrast
- module: ui, backend: local, level: 0
- Text/background contrast math

## ui.design_brief
- module: ui, backend: local, level: 0
- NL description -> brief+strategy

## ui.validate_layout
- module: ui, backend: local, level: 0
- Inventory slot/action/text checks
