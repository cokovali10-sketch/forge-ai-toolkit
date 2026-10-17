<div align="center">

# ◆ FORGE AI Toolkit

### Внешний инструментарий для ИИ-агентов · External toolkit for AI agents

[![tests](https://img.shields.io/badge/tests-178_passing-4ade80?style=for-the-badge)](#)
[![python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](#)
[![license](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](#)
[![offline](https://img.shields.io/badge/offline-no_cloud-8b5cf6?style=for-the-badge)](#)

| | |
|---|---|
| 🇷🇺 | **[Читать на русском →](./README_RU.md)** |
| 🇬🇧 | **[Read in English →](./README_EN.md)** |

*Выбери язык · Choose your language*

</div>

---

<div align="center">

**Конвейер, который сам себя проверяет · A pipeline that checks itself**

```bat
.venv\Scripts\python -m forge.cli pipe run <project-dir>
```

```json
// Тот же конвейер для ИИ-агента (MCP):
{ "tool": "pipe.run", "args": { "root": "<project-dir>" } }
```

[📦 Релизы](https://github.com/cokovali10-sketch/forge-ai-toolkit/releases) · [🛠 Исходники](./src/forge) · [📜 Changelog](./CHANGELOG.md)

</div>

---

## Что это · What is this

| 🇷🇺 Русский | 🇬🇧 English |
|---|---|
| FORGE подключается к твоему ИИ-агенту и даёт ему руки: конвейер проверок для **любых проектов на любых языках** (Python, JS, Rust, C++, Go, Java...), 32 своих инструмента + 120 Anvil + ~200 Hermes, редактор объектов, база знаний, а для Minecraft — бонусом настоящая тестовая лаборатория с живым сервером. Без обучения моделей, без платных API, без выдуманных результатов. | FORGE plugs into your AI agent and gives it hands: a check conveyor for **any projects in any languages** (Python, JS, Rust, C++, Go, Java...), 32 native tools + 120 Anvil + ~200 Hermes ones, an object editor, a knowledge base — plus a real live-server testing lab for Minecraft. No model training, no paid APIs, no hallucinated results. |

## Людям · For humans

```bat
python -m venv .venv
.venv\Scripts\python -m pip install -e forge
.venv\Scripts\python -m pytest forge\tests -q
.venv\Scripts\python -m forge.cli gen web --name shop --out ./shop
.venv\Scripts\python -m forge.cli pipe window <project-dir>
```

## ИИ-агентам · For AI agents

```json
{
  "mcpServers": {
    "forge": {
      "command": "D:/Forge-Factority/.venv/Scripts/python.exe",
      "args": ["-m", "forge.cli", "mcp"],
      "cwd": "D:/Forge-Factority"
    }
  }
}
```

<div align="center">

**🇷🇺 [Полная инструкция на русском →](./README_RU.md) · 🇬🇧 [Full instructions in English →](./README_EN.md)**

</div>
