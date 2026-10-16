# FORGE AI Toolkit

> **RU:** Внешний инструментарий для ИИ-агентов: экспертные навыки, MCP-сервер,
> анализ проектов, тестовая лаборатория Minecraft/Java. Без обучения моделей,
> без платных API, без выдумок — только проверяемые инструменты.
>
> **EN:** External toolkit for AI agents: expert skills, MCP server, project
> intelligence, Minecraft/Java testing lab. No model training, no paid APIs,
> no hallucinated results — only verifiable tools.

## Что это / What is this

FORGE подключается к существующему ИИ-агенту и даёт ему: знания с поиском,
переносимые Skills, ~120 инструментов Anvil + сервисы Hermes через один CLI,
MCP-сервер для совместимых клиентов и изолированную Testing Lab, где плагины
реально собираются и гоняются на настоящем сервере.

FORGE plugs into your existing AI agent and gives it: searchable knowledge,
portable Skills, ~120 Anvil tools + Hermes services behind one CLI, an MCP
server for compatible clients, and an isolated Testing Lab where plugins are
really built and run against a real server.

## Быстрый старт / Quickstart

```bat
python -m venv .venv
.venv\Scripts\python -m pip install -e forge
.venv\Scripts\python -m pytest forge\tests -q
.venv\Scripts\python -m forge.cli modules
.venv\Scripts\python -m forge.cli pipe run <project-dir>
```

## Возможности / Features

- Skills (java-expert, paper-plugin-expert, build-repair, ...) с валидацией
- Module packs + Expert Router (`forge route "..."`)
- SQLite FTS база знаний (`forge know ...`)
- MCP-сервер, проверенный официальным SDK-клиентом
- Testing Lab: сборка, unit-тесты, реальный Purpur, команды, отчёты
- AAA Interface Engine: брифы, стратегии A/B/C/D, валидация GUI, PNG-ассеты
- Генератор Paper-плагинов (`forge gen paper ...`)
- Стандарт ToolResult + уровни разрешений 0–4 (`docs/permissions.md`)
- Жизненный цикл модулей (enable/disable), генерируемые каталоги (`forge docs`)
- Конвейер `pipe`: осмотр → ревью → скиллы → знания. Headless для ИИ
  (`forge pipe run`, JSON + exit codes + чекпоинты), окно для человека
  (`forge pipe window`, tkinter, ноль зависимостей). Как MCP-инструменты
  (`pipe.stages`/`pipe.run`/`pipe.status`), выборочные стадии (`--only`),
  подавитель шума (`.forge-suppress.json`), история прогонов, кнопка «Продолжить»,
  слежка за файлами (`forge pipe watch`, кнопка «👁 Следить» в окне),
  инкрементальность по контент-хэшам (перезапускаются только затронутые
  стадии — повторный прогон берётся из кэша чекпоинта),
  тяжёлая стадия `lab-e2e` (настоящий Purpur, только `--heavy` / `--only lab-e2e`),
  параллельные быстрые стадии (`--serial` возвращает очередь),
  вкладка истории прогонов и таймер в окне

## Статус / Status

Ядро + Testing Lab + UI Engine работают и покрыты тестами (55 тестов).
Десктоп отложен (нужен Node.js). Скриншоты и автоклиент честно отмечены
как NOT_IMPLEMENTED.

## Лицензия / License

MIT — см. `forge/LICENSE`.
