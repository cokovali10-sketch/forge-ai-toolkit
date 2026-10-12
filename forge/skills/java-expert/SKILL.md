---
name: java-expert
version: 0.1.0
domain: java
---
# Java Expert

Battle-tested rules for Java 17/21/25 + Gradle work.

## Build discipline
- Never guess dependency versions: resolve from metadata (meta.fabricmc.net,
  maven central, gradle plugins portal) before writing build files.
- Gradle/loom/JDK compatibility is a matrix, not a guess: loom 1.13 needs
  Gradle 8.14; loom 1.16 needs Gradle 9.4 + JDK 25. Verify with a real build.
- `release = <n>` must match the toolchain JDK that actually compiles.

## Mapping discipline (Minecraft/Fabric)
- Yarn names != Mojang names. Verify every FQN against the real jar
  (javap on the mapped artifact), never from memory alone.
- 26.x line is UNOBFUSCATED: loom 1.16 + `net.fabricmc.fabric-loom` plugin id
  + Mojang names, no Yarn (yarn/26.x is empty, intermediary is 0.0.0).
- Input/render APIs drift between lines: KeyBinding->KeyMapping,
  DrawContext->GuiGraphicsExtractor, Screen.render->extractRenderState.

## Runtime discipline
- Never call display/native-backed APIs before the window exists
  (e.g. key display names resolve via native glfwGetKeyName and crash startup).
- Isolate per-element failures; disable repeat offenders; log once.
- Unit-test pure logic; treat environment flakes (locked temp dirs) as flakes:
  rerun before blaming code.
