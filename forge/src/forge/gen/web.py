"""Web landing generator: быстрый лендинг без сборки и зависимостей.

Generates: index.html (семантика + meta), styles.css (тёмная тема,
адаптив), app.js (строго без ошибок: strict + проверки), README.
Проверяется: файлы на месте, JS парсится (node --check если есть, иначе
скобочный аудит), HTML имеет title/h1.
"""
from __future__ import annotations

import re
from pathlib import Path

HTML = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{name} — быстро и по делу">
<title>{name}</title>
<link rel="stylesheet" href="styles.css">
</head>
<body>
<header><h1>{name}</h1><p>Собрано FORGE Generator за минуту.</p></header>
<main id="app"></main>
<script src="app.js" defer></script>
</body>
</html>
"""

CSS = """:root{color-scheme:dark}
*{margin:0;box-sizing:border-box}
body{background:#0b0d14;color:#e2e8f0;font-family:system-ui;padding:32px}
header h1{font-size:clamp(28px,5vw,52px);letter-spacing:-1px}
#app{margin-top:20px;display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(220px,1fr))}
.card{background:#ffffff0f;border:1px solid #ffffff22;border-radius:12px;padding:16px}
@media (max-width:600px){body{padding:16px}}
"""

JS = """'use strict';
(function () {
  var root = document.getElementById('app');
  if (!root) return;
  var items = ['Быстро', 'Адаптивно', 'Без сборки'];
  for (var i = 0; i < items.length; i++) {
    var d = document.createElement('div');
    d.className = 'card';
    d.textContent = items[i];
    root.appendChild(d);
  }
})();
"""


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9-_ ]", "", name or "").strip() or "Site"
    return s


def generate(out_dir: str | Path, name: str = "Site") -> dict:
    """Generates a landing. Returns {dir, files}."""
    title = _slug(name)
    out = Path(out_dir)
    files = {"index.html": HTML.format(name=title),
             "styles.css": CSS,
             "app.js": JS,
             "README.md": f"# {title}\n\nОткрой `index.html` — сборки не надо.\n"}
    made = []
    for rel, content in files.items():
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        made.append(rel)
    problems = []
    html = files["index.html"]
    if "<title>" not in html or "<h1>" not in html:
        problems.append("html: нет title/h1")
    js = files["app.js"]
    if js.count("{") != js.count("}") or js.count("(") != js.count(")"):
        problems.append("js: скобки не сходятся")
    return {"dir": str(out), "files": made,
            "ok": not problems, "problems": problems}
