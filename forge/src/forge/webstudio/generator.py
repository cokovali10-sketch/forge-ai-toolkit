"""Web Studio generator: HTML + CSS + JS + spec, then an honest audit.

The output is a complete static site: no build step, no package manager,
no CDN. Open index.html and it works.
"""
from __future__ import annotations

import html as _html
import json
import re
from pathlib import Path

from . import site_audit as _audit
from .content import ICONS, copy_for, normalize_text
from .motion import MOTION_JS
from .presets import DEFAULT_PRESET, PRESETS, get
from .styles import build as build_css

KNOWN_ANIMATIONS = ["reveal", "tilt", "magnet", "particles", "counter",
                    "parallax", "marquee", "glitch"]


def _esc(text: str) -> str:
    return _html.escape(str(text or ""), quote=True)


def _title(name: str) -> str:
    text = " ".join((name or "").split())
    text = re.sub(r"[<>{}\\]", "", text)[:80]
    return text or "Site"


def _attr(flag: bool, attr: str, value: str = "") -> str:
    if not flag:
        return ""
    return f' {attr}="{_esc(value)}"' if value else f" {attr}"


def _html_page(name: str, preset_key: str, preset: dict, tagline: str,
               lang: str, animations: list[str]) -> str:
    c = copy_for(lang)
    has = lambda key: key in animations  # noqa: E731
    title = _title(name)
    lead = normalize_text(tagline, c["lead"])
    tilt = _attr(has("tilt"), "data-tilt", "8")
    magnet = _attr(has("magnet"), "data-magnet")
    parallax = _attr(has("parallax"), "data-parallax", "0.08")
    count = lambda value: (f' data-count="{value}"' if has("counter")  # noqa: E731
                           else "")
    reveal = _attr(has("reveal"), "data-reveal")

    nav_links = "".join(
        f'<a href="#{anchor}">{_esc(label)}</a>'
        for anchor, label in c["nav"])
    features = "".join(
        f'<article class="card"{reveal}{tilt} data-delay="{i * 90}">'
        f'<div class="icon">{ICONS.get(icon, ICONS["spark"])}</div>'
        f"<h3>{_esc(f_title)}</h3><p>{_esc(f_text)}</p></article>"
        for i, (icon, f_title, f_text) in enumerate(c["features"]))
    shots = "".join(
        f'<figure class="shot"{reveal} data-delay="{i * 90}">'
        f'<div class="shot-ui"{parallax}>'
        f'<div class="shot-bar"><i></i><i></i><i></i></div>'
        f'<span class="shot-line w1"></span>'
        f'<span class="shot-line w2"></span>'
        f'<span class="shot-line w3"></span>'
        f'<span class="shot-blob"></span></div>'
        f"<figcaption><b>{_esc(s_label)}</b>"
        f"<span>{_esc(s_text)}</span></figcaption></figure>"
        for i, (s_label, _s_tag, s_text) in enumerate(c["shots"]))
    stats = "".join(
        f'<div class="stat"{reveal}><b{count(value)}>{value}{_esc(suffix)}</b>'
        f"<span>{_esc(label)}</span></div>"
        for value, suffix, label in c["stats"])
    hero_metrics = "".join(
        f'<div class="metric"><b{count(value)}>{value}{_esc(suffix)}</b>'
        f"<span>{_esc(label)}</span></div>"
        for value, suffix, label in c["metric"])
    rows = "".join(
        f'<div class="panel-row"><span>{_esc(k)}</span><b>{_esc(v)}</b></div>'
        for k, v in c["panel_rows"])

    canvas = ('<canvas id="fx" data-particles aria-hidden="true"></canvas>'
              if has("particles") else "")
    glitch = ""
    if has("glitch"):
        glitch = (f'<p class="glitch-line" aria-hidden="true">'
                  f'{_esc(" · ".join(c["glitch_words"]))}</p>')
    marquee = ""
    if has("marquee"):
        chunk = _esc(c["marquee"]) * 4
        marquee = (f'<div class="marquee" aria-hidden="true">'
                   f'<div class="marquee-track"><span>{chunk}</span>'
                   f'<span>{chunk}</span></div></div>')

    return f"""<!doctype html>
<html lang="{_esc(c['lang'])}" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{_esc(lead)}">
<meta name="theme-color" content="{_esc(preset['colors']['bg'])}">
<title>{_esc(title)}</title>
<link rel="stylesheet" href="styles.css">
</head>
<body class="preset-{_esc(preset_key)} effect-{_esc(preset['effect'])}">
<a class="skip" href="#main">{_esc(c['skip'])}</a>
<div class="bg" aria-hidden="true">
  <span class="orb orb-1"></span>
  <span class="orb orb-2"></span>
  <span class="orb orb-3"></span>
  <span class="grid"></span>
  {canvas}
</div>
<header class="nav"{reveal}>
  <a class="brand" href="#top"><span class="mark"></span>{_esc(title)}</a>
  <nav class="nav-links" aria-label="Navigation">
    {nav_links}
    <a class="btn btn-ghost" href="#cta">{_esc(c['nav_cta'])}</a>
  </nav>
</header>
{marquee}
<main id="main">
  <section class="hero" id="top">
    <div class="hero-copy">
      <p class="eyebrow"{reveal}>{_esc(c['eyebrow'])}</p>
      <h1><span class="h1-anim"{reveal}>{_esc(c['hero_a'])}<br><span class="grad">{_esc(c['hero_b'])}</span></span></h1>
      <p class="lead"{reveal}>{_esc(lead)}</p>
      {glitch}
      <div class="cta-row"{reveal}>
        <a class="btn btn-primary" href="#cta"{magnet}>{_esc(c['cta_primary'])}</a>
        <a class="btn btn-ghost" href="#showcase"{magnet}>{_esc(c['cta_secondary'])}</a>
      </div>
    </div>
    <aside class="hero-panel"{reveal}{tilt}>
      <div class="panel-head"><span class="dot"></span>{_esc(c['panel_title'])}</div>
      <div class="panel-body">
        {rows}
        <div class="metrics">{hero_metrics}</div>
      </div>
    </aside>
  </section>

  <section class="section" id="features">
    <div class="sec-head"{reveal}>
      <p class="kicker">{_esc(c['sec_features_kicker'])}</p>
      <h2>{_esc(c['sec_features_title'])}</h2>
      <p>{_esc(c['sec_features_lead'])}</p>
    </div>
    <div class="cards">{features}</div>
  </section>

  <section class="section" id="showcase">
    <div class="sec-head"{reveal}>
      <p class="kicker">{_esc(c['sec_showcase_kicker'])}</p>
      <h2>{_esc(c['sec_showcase_title'])}</h2>
      <p>{_esc(c['sec_showcase_lead'])}</p>
    </div>
    <div class="gallery">{shots}</div>
  </section>

  <section class="section stats" id="stats">
    {stats}
  </section>

  <section class="section cta" id="cta">
    <div class="cta-card"{reveal}{tilt}>
      <h2>{_esc(c['cta_title'])}</h2>
      <p>{_esc(c['cta_text'])}</p>
      <a class="btn btn-primary" href="#top"{magnet}>{_esc(c['cta_button'])}</a>
    </div>
  </section>
</main>
<footer class="footer">
  <span>{_esc(c['footer'])}</span>
  <span>{_esc(title)} · {_esc(preset['title'])}</span>
</footer>
<div class="cursor-glow" aria-hidden="true"></div>
<script src="app.js" defer></script>
</body>
</html>
"""


def _readme(title: str, preset_key: str, animations: list[str]) -> str:
    return f"""# {title}

Generated by **FORGE Web Studio** — a static site with no build step,
no dependencies and no CDN. Open `index.html` in a browser.

- preset: `{preset_key}`
- animations: {", ".join(animations) if animations else "none"}
- files: `index.html`, `styles.css`, `app.js`, `site.json`

## Commands

```bat
forge web new "{title}" --preset {preset_key} --out .
forge web audit .
forge web preview .
```

## Customize

Colors, fonts, radius and animations live in `site.json` and the CSS
custom properties at the top of `styles.css`. All motion is disabled
automatically for `prefers-reduced-motion: reduce`.
"""


def generate(out_dir: str | Path, name: str = "Site",
             preset: str = DEFAULT_PRESET, tagline: str = "",
             lang: str = "ru", sections: list[str] | None = None,
             animations: list[str] | None = None) -> dict:
    """Generate a complete static site and audit it immediately."""
    key = (preset or DEFAULT_PRESET).strip().lower()
    data = get(key)
    chosen = [a for a in (animations or data["animations"])
              if a in KNOWN_ANIMATIONS]
    title = _title(name)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    spec = {
        "name": title,
        "tagline": tagline,
        "lang": "en" if str(lang).lower().startswith("en") else "ru",
        "preset": key,
        "animations": chosen,
        "sections": sections or ["hero", "features", "showcase", "stats", "cta"],
        "generator": "forge-webstudio",
        "version": "1.0.0",
    }
    files = {
        "index.html": _html_page(title, key, data, tagline, lang, chosen),
        "styles.css": build_css(data),
        "app.js": MOTION_JS,
        "README.md": _readme(title, key, chosen),
        "site.json": json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
    }
    made = []
    for rel, content in files.items():
        path = out / rel
        path.write_text(content, encoding="utf-8")
        made.append(rel)

    result = _audit.audit(out, key)
    return {
        "ok": result["ok"],
        "dir": str(out),
        "files": made,
        "preset": key,
        "preset_title": data["title"],
        "animations": chosen,
        "score": result["score"],
        "audit": result,
        "problems": result["problems"],
    }
