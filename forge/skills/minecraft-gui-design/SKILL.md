---
name: minecraft-gui-design
version: 0.1.0
domain: design
activate-when:
  - task mentions Minecraft GUI, inventory menu, clan/shop/auction GUI
  - chest/inventory menu code present
verify-by:
  - slot map documented; no orphan buttons; RU+EN labels present
  - navigation (back/close/pagination) works on every screen
limits:
  - never mix web design with Minecraft GUI primitives
  - one click = one action; confirm destructive actions
---
# Minecraft GUI Design

## Layout rules
- Map every slot: content, filler, navigation, info. No dead buttons.
- Paginate lists (36 content slots max per page); always show page/total.
- Back/close buttons on every screen; ESC behavior defined.

## States
- Design empty, loading, error and no-permission states, not just happy path.
- Confirm destructive actions (delete/reset) with a second click.

## Text
- Full RU + EN localization from day one; no hardcoded strings in logic.
- Color for hierarchy, not decoration; keep contrast readable on dark panes.

## Knowledge sources
- knowledge base domain=design; prior auction/titles GUI patterns.

## Quality bar
- Review checklist passes: hierarchy, consistency, states, localization.
