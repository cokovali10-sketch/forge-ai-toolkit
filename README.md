<div align="center">

# ◆ FORGE AI Toolkit

**Универсальный инструмент разработки для AI-агентов: конвейер проверок, MCP-сервер,
языковые эксперты, автофиксы, база знаний и живая лаборатория для Minecraft.**

Без обучения моделей, без платных API, без выдумок — только проверяемые инструменты.

[![CI](https://github.com/cokovali10-sketch/forge-ai-toolkit/actions/workflows/forge.yml/badge.svg)](https://github.com/cokovali10-sketch/forge-ai-toolkit/actions/workflows/forge.yml)
[![tests](https://img.shields.io/badge/tests-235_passing-4ade80?style=for-the-badge)](#статус-и-честность)
[![python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](#быстрый-старт)
[![mcp](https://img.shields.io/badge/MCP-72_tools-8b5cf6?style=for-the-badge)](#mcp-72-инструмента)
[![license](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](./LICENSE)
[![offline](https://img.shields.io/badge/offline-no_cloud-0ea5e9?style=for-the-badge)](#безопасность)

**Русский** · [English](./forge/README_EN.md) · [Полная инструкция](./forge/README_RU.md) · [Архитектура](./forge/docs/architecture.md) · [Каталог инструментов](./forge/docs/tools.md) · [Issues](https://github.com/cokovali10-sketch/forge-ai-toolkit/issues)

</div>

---

## Что такое FORGE

Обычный ИИ-агент умеет рассуждать, но у него нет рук: он не соберёт проект,
не прогонит тесты на настоящем сервере и не проверит сотни файлов за секунду.
FORGE — это руки. Один CLI и один MCP-сервер дают агенту (и человеку) полный
набор проверяемых операций над проектом на **любом языке**.

| Для человека | Для ИИ-агента |
|---|---|
| Окно с кнопками, графиками и историей: `pipe window` | Те же проверки без окна: JSON + exit-коды: `pipe run` |
| Локальный дашборд: `forge serve` | Один вызов: `pipe.run`, `report.full`, `audit.run` |

**Ничего не выдумывается:** нет тулчейна — честное «пропущено»; не готово —
`NOT_IMPLEMENTED`; сомнение помечается как сомнение.

---

## Быстрый старт

```bat
git clone https://github.com/cokovali10-sketch/forge-ai-toolkit.git
cd forge-ai-toolkit
python -m venv .venv
.venv\Scripts\python -m pip install -e forge
.venv\Scripts\python -m pytest forge\tests -q
```

Готово, если тесты зелёные. Дальше:

```bat
.venv\Scripts\python -m forge.cli modules
.venv\Scripts\python -m forge.cli audit <проект>
.venv\Scripts\python -m forge.cli pipe run <проект>
.venv\Scripts\python -m forge.cli serve <проект> --open
```

---

## Масштаб

**72 MCP-инструмента**, **19 модулей**, **5 пакетов экспертов**, **8 стадий конвейера**, **233 теста**.

| Блок | Что делает |
|---|---|
| `kit` | `map`, `test`, `ci`, `secrets`, `deps`, `doctor`, `audit`, `init`, `report`, `baseline` — здоровье и онбординг любого проекта |
| `pipe` | Конвейер проверок: осмотр → секреты → ревью → скиллы → знания → языки → чистый код → (опц.) живой e2e |
| `refactor` | Советник по чистому коду: длинные функции, вложенность, дубли, магические числа, мёртвый код + оценка 0..100; `apply`/`fix_dir` с бэкапом и откатом; SARIF |
| `loop` / `do` / `quality` | Автопилот: намерение → план → конвейер → ремонт → повтор; тренд качества и регресс-гейт для CI |
| `langs` | 5 языковых экспертов: Python, JS/TS, Rust, C++, Go (detect / lint / test / scaffold) |
| `gen` / `make` | Генераторы: landing, python-service, go-cli, node-api, rust-cli, Paper-плагин — плюс `make` = генерация + проверка |
| `speed` | Скорость агента: много файлов и правок одной транзакцией, поиск одним проходом, контекст-пак, каркасы сложных структур |
| `webstudio` | Web Studio: 6 анимированных пресетов, motion без зависимостей, RU/EN, аудит сайта 0..100, превью |
| `factory` | Фабрика плагинов: намерение → GUI-плагин → javac → настоящий Purpur e2e → zip + отчёт |
| `studio` | Многопроектная студия в браузере: реестр проектов, аудит, пайплайн, генераторы, экспорт |
| `lab` | Живая лаборатория: настоящая сборка Gradle/Maven и запуск тестов на реальном сервере (Minecraft) |
| `minecraft` | Проверки плагинов через Anvil: metadata, api-version, permissions, анализ логов |
| `edit` | Редактор объектов: JSON свой, YAML через Anvil; backup / validate / rollback |
| `knowledge` / `skills` | База знаний с FTS и скиллы-процедуры (`paper-plugin-expert`, `java-expert`, `build-repair`, `refactor-expert`, `security-audit`, `minecraft-gui-design`, `speed-coder`) |
| `ui` | Дизайн-брифы, контраст, валидация layout-ов инвентаря |
| `project` | Безопасные операции чтения: `inspect`, `tree`, `read_file`, `search` (workspace-confined, секреты вычищаются) |

Помимо своего арсенала FORGE подключает **~120 инструментов Anvil** и **~200 Hermes**
за тем же CLI и MCP-сервером.

---

## Скорость: один вызов вместо десяти

Главный тормоз агента — не набор текста, а число обращений к инструментам.
Отдел `speed` убирает round-trip-ы: одна операция пишет десятки файлов, правит
десятки мест, ищет все шаблоны за один проход и отдаёт нужный кусок репозитория
целиком.

```bat
forge fast context --root . --query "class .*Service" --json   :: дерево + файлы
forge fast search --root . --pattern TODO --pattern FIXME      :: один проход
forge fast write --root . --spec files.json                    :: атомарная запись
forge fast patch --root . --spec edits.json                    :: атомарные правки
forge fast blueprint --root D:\work\shop --template plugin-feature --name "Shop"
forge fast bench --root . --files 80                           :: честный замер
```

| Инструмент | Что делает |
|---|---|
| `speed.write` | Много файлов за вызов: `atomic`-откат, `base64`, `append`, `dry_run` |
| `speed.patch` | Много exact/regex-правок: `expected=N`, `all`, diff, одна транзакция |
| `speed.search` | Все шаблоны за один проход, контекст строк, секреты вычищаются |
| `speed.context` | Дерево + выбранные файлы одним ответом, бюджет символов/токенов |
| `speed.blueprint` | Каркас целиком: `python-package`, `layered`, `http-service`, `plugin-feature`, `custom` |
| `speed.bench` | Диск и «эффективное» время с учётом round-trip |

Замер на референсной машине (80 файлов, 2 мс на вызов): запись **3.60x**,
атомарная запись **2.11x**, пакетные правки **2.16x**, 4 поиска за один проход
**3.27x**. Диск в батче может быть медленнее — выигрыш в устранении вызовов;
цифры проверяются `forge fast bench`, а не принимаются на веру.
Подробности: [docs/speed.md](./forge/docs/speed.md).

---

## Конвейер проверок

```
inspect → secrets → review → skills → knowledge → langs → clean-code → lab-e2e
```

- быстрые стадии идут параллельно, тяжёлая — строго после и только на зелёных;
- повторные прогоны берут неизменённое из кэша по контент-хэшам;
- `--changed` проверяет только изменённые git-файлы (hold-the-line);
- шум подавляется только с причиной (`.forge-suppress.json`) или `# forge-ignore`;
- `pipe heal` делает страховку, лечит и откатывает при неудаче.

```bat
forge pipe run .            :: разовый прогон
forge pipe watch .          :: слежка за изменениями
forge pipe window .         :: окно с кнопками и историей
forge pipe heal .           :: контрольная точка + ремонт + проверка
```

---

## MCP: 72 инструмента

Любой MCP-клиент (Claude Desktop и др.) подключается к FORGE как к локальному серверу:

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

Уровни разрешений 0–4: чтение — 0, запуск тулчейнов — 1, сборка и запись — 2.
Клиент сам решает, что разрешить агенту. Полный список — [docs/tools.md](./forge/docs/tools.md).

---

## CLI-шпаргалка

| Команда | Что делает |
|---|---|
| `forge map <dir>` | Языки, LOC, точки входа, граф импортов, зависимости |
| `forge test <dir>` | Родные тесты проекта (pytest/npm/go/cargo/gradle/maven/make) |
| `forge secrets <dir>` | Поиск утечек (вывод маскируется) |
| `forge deps <dir>` | Зависимости всех экосистем + гигиена версий |
| `forge audit <dir>` | Сводное здоровье проекта, балл 0..100, гейт `--min-score` |
| `forge init [dir]` | CI-workflow + заглушка подавлений, без перезаписи |
| `forge report [dir]` | Единый свод: audit + тренд + конвейер + арена |
| `forge serve [dir]` | Локальный дашборд и JSON API (`/api/report`, `/api/health`) |
| `forge studio` | Студия для нескольких проектов: аудит, пайплайн, генераторы, превью |
| `forge web presets\|new\|audit` | Анимированные сайты и их аудит |
| `forge factory "<намерение>"` | Плагин под ключ: генерация, сборка, живой e2e, zip |
| `forge fast write\|patch\|search\|context\|blueprint` | Скорость: пакетные файлы и правки, поиск одним проходом, контекст, каркасы |
| `forge baseline save\|check` | Падать только на **новых** проблемах |
| `forge fix [dir]` | Пакетные безопасные автофиксы с общим откатом |
| `forge refactor <file\|dir>` | План чистого кода, SARIF, `--apply` |
| `forge do "<намерение>"` | Оркестратор: цех + модули + скиллы + план |
| `forge loop <dir>` | Замкнутый контур: конвейер → ремонт → повтор |
| `forge quality <dir>` | Дашборд качества, тренд, регресс-гейт |
| `forge know "<запрос>"` | База знаний (майнер — только вручную) |
| `forge gen <тип> <имя>` | Генераторы проектов |
| `forge lab e2e` | Настоящая сборка и тесты на живом сервере |

---

## Структура репозитория

```
forge-ai-toolkit/
├── README.md                 <- эта страница
├── LICENSE                   <- MIT
├── .github/workflows/        <- CI и release
└── forge/
    ├── src/forge/            <- код (cli, mcp, kit, pipe, refactor, langs, gen, speed, lab, ...)
    ├── tests/                <- 233 теста
    ├── docs/                 <- архитектура, инструменты, модули, права, UI, lab
    ├── skills/               <- скиллы-процедуры для агентов
    ├── benchmarks/           <- арена и табло
    ├── README_RU.md          <- полная инструкция (RU)
    ├── README_EN.md          <- full guide (EN)
    ├── CHANGELOG.md
    └── pyproject.toml
```

---

## Документация

- [Полная инструкция (RU)](./forge/README_RU.md) · [Full guide (EN)](./forge/README_EN.md)
- [Архитектура](./forge/docs/architecture.md)
- [Каталог 72 инструментов](./forge/docs/tools.md)
- [Модули и пакеты](./forge/docs/modules.md)
- [Скорость: batch, контекст, каркасы](./forge/docs/speed.md)
- [Уровни разрешений](./forge/docs/permissions.md)
- [Тестовая лаборатория](./forge/docs/testing-lab.md)
- [UI-движок](./forge/docs/ui-engine.md)
- [CHANGELOG](./forge/CHANGELOG.md)

---

## Безопасность

- чтение чужих проектов с лимитами, без симлинков, ошибки доступа игнорируются;
- записи — только свои артефакты, история ротируется;
- `heal` делает контрольную точку до любых изменений;
- майнер и вотчеры **никогда** не включаются сами;
- секреты не читаются и не печатаются — только маска.

---

## Статус и честность

- **233 теста** — зелёные; self-audit: **82/100**, секретов 0.
- Работает: ядро, конвейер, лаборатория, 5 языков, редактор, генераторы,
  `speed` (пакетные файлы/правки, контекст, каркасы), `refactor`, автопилот,
  `serve`/`report`, `baseline`, `fix`, `init`.
- Честно не готово: десктоп-приложение (нужен Rust/Tauri), скриншоты GUI,
  публикация на PyPI (workflow готов, нужен trusted-publisher).
- Реальный прогон арены моделью — в планах; сейчас валидируется harness.

---

## Участие

- Баг или идея — [issue](https://github.com/cokovali10-sketch/forge-ai-toolkit/issues).
- Перед pull request: `python -m pytest forge/tests -q`, затем `python -m forge.cli pipe run forge`.
- Ядро без новых зависимостей; вместо заглушек — честный `NOT_IMPLEMENTED`.

---

## Лицензия

MIT — см. [LICENSE](./LICENSE).

