# AAA Interface Engine (FORGE/UI)

Design briefs, rendering strategies, component validation and programmatic
asset production. Minecraft-first, engine-agnostic core.

## Commands

```bat
REM brief: RU or EN description -> style/screens/features/strategy
python -m forge.cli ui brief "Премиальный аукцион dark fantasy с поиском"
REM asset pack: 5 real PNGs + manifest + pack.mcmeta
python -m forge.cli ui pack
```

## Strategies (honest docs in `ui/strategy.py`)

- **A Inventory GUI** — standard Paper menus, works everywhere.
- **B Resource-Pack UI** — fonts/glyphs/frames, degrades to A.
- **C Client-Side UI** — needs a client mod (MythicVisuals-class).
- **D Hybrid** — layers combined, per-layer degradation.

## Validation without screenshots

- `ui.validate_layout` — 54-slot rules, overlaps, orphan buttons, text length.
- `ui.check_contrast` — WCAG-ish luminance math on ARGB pairs.
- `layout.json` of every demo must validate (enforced by tests).

## Demo: MythicShop

`examples/mythic-shop/`: Paper plugin (categories, emerald prices,
server-side buy, dupe-safe cancel) + generated dark-red PNG pack +
`pack.mcmeta` + validated `layout.json`.

Verified 2026-10-12: compiles clean, boots on Purpur 1.21.11,
`/mythicshop` console path returns `console-ok`, log clean (8/8 lab checks).

## Limits (honest)

- No image-gen AI here: textures are procedural (PIL). Real art direction
  needs an image tool or an artist.
- No client automation: no click-through or screenshot diffs (see lab limits).
- Line-outline rendering needs the 26.x submit pipeline + in-game runs;
  block highlights use particles instead.
