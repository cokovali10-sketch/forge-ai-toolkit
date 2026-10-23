"""Static audit for generated sites: structure, contrast, motion, weight.

Honest checks only: file presence, parseable JS (node when available),
WCAG contrast math on the preset tokens, offline safety and a size budget.
No screenshots, no browser required.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from .presets import DEFAULT_PRESET, PRESETS


def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = (hex_color or "").strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) != 6:
        raise ValueError(f"not a hex color: {hex_color!r}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _luminance(hex_color: str) -> float:
    def channel(value: int) -> float:
        v = value / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = _rgb(hex_color)
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(fg: str, bg: str) -> float:
    a, b = _luminance(fg), _luminance(bg)
    lo, hi = min(a, b), max(a, b)
    return round((hi + 0.05) / (lo + 0.05), 2)


def _js_syntax(path: Path) -> tuple[bool, str]:
    node = shutil.which("node")
    if node:
        try:
            r = subprocess.run([node, "--check", str(path)],
                               capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                return True, "node --check ok"
            return False, ((r.stderr or r.stdout).strip()[:300]
                           or f"node --check exit {r.returncode}")
        except (OSError, subprocess.TimeoutExpired) as e:
            return False, f"node --check failed to run: {e}"
    text = path.read_text(encoding="utf-8", errors="replace")
    pairs = [("{", "}"), ("(", ")"), ("[", "]")]
    for left, right in pairs:
        if text.count(left) != text.count(right):
            return False, f"bracket mismatch {left}{right}"
    return True, "bracket audit (node not found)"


def _check(checks: list, name: str, ok: bool, detail: str = "",
           severity: str = "high") -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": detail,
                   "severity": severity})


def audit(out_dir: str | Path, preset_key: str = "") -> dict:
    base = Path(out_dir)
    checks: list[dict] = []
    problems: list[str] = []

    files = ["index.html", "styles.css", "app.js", "README.md", "site.json"]
    missing = [f for f in files if not (base / f).is_file()]
    _check(checks, "files", not missing,
           "all 5 files present" if not missing else "missing: " + ", ".join(missing))
    if missing:
        return {"ok": False, "score": 0, "preset": preset_key or DEFAULT_PRESET,
                "checks": checks, "problems": ["missing files: " + ", ".join(missing)],
                "stats": {"files": 0, "bytes": 0}}

    html = (base / "index.html").read_text(encoding="utf-8")
    css = (base / "styles.css").read_text(encoding="utf-8")
    js = (base / "app.js").read_text(encoding="utf-8")

    key = preset_key
    if not key:
        try:
            key = json.loads((base / "site.json").read_text(encoding="utf-8")).get(
                "preset", DEFAULT_PRESET)
        except (OSError, ValueError):
            key = DEFAULT_PRESET
    preset = PRESETS.get(key, PRESETS[DEFAULT_PRESET])

    for name, ok, detail in (
        ("doctype", html.lstrip().lower().startswith("<!doctype html>"),
         "html5 doctype"),
        ("lang", bool(re.search(r"<html[^>]+lang=", html)), "html lang set"),
        ("viewport", 'name="viewport"' in html, "responsive meta"),
        ("description", 'name="description"' in html, "meta description"),
        ("title", bool(re.search(r"<title>[^<]+</title>", html)), "non-empty title"),
        ("h1", html.count("<h1") == 1, "exactly one h1"),
        ("landmarks", "<main" in html and "<footer" in html,
         "main + footer landmarks"),
        ("skip-link", 'class="skip"' in html, "keyboard skip link"),
        ("offline", not re.search(r'(?:src|href|url)\s*[=(]\s*["\']?https?://',
                                  html + css + js),
         "no external http(s) assets"),
    ):
        _check(checks, name, ok, detail)
        if not ok:
            problems.append(f"{name}: {detail} failed")

    js_ok, js_detail = _js_syntax(base / "app.js")
    _check(checks, "js-syntax", js_ok, js_detail)
    if not js_ok:
        problems.append(f"js-syntax: {js_detail}")

    for name, ok, detail in (
        ("reduced-motion", "prefers-reduced-motion" in css
         and "prefers-reduced-motion" in js,
         "CSS + JS respect the user preference"),
        ("strict-js", "'use strict'" in js or '"use strict"' in js,
         "strict mode enabled"),
        ("motion-primitives", "IntersectionObserver" in js,
         "reveal uses IntersectionObserver"),
        ("reveal-guard", ".no-js [data-reveal]" in css,
         "content visible without JS"),
    ):
        _check(checks, name, ok, detail, severity="medium")
        if not ok:
            problems.append(f"{name}: {detail} failed")

    total = sum((base / f).stat().st_size for f in files)
    _check(checks, "weight", total <= 250 * 1024,
           f"{total / 1024:.1f} KB total (budget 250 KB)")
    if total > 250 * 1024:
        problems.append(f"weight: {total / 1024:.1f} KB > 250 KB")

    c = preset["colors"]
    pairs = [
        ("text-on-bg", c["text"], c["bg"], 4.5),
        ("muted-on-bg", c["muted"], c["bg"], 4.5),
        ("accent-on-bg", c["accent"], c["bg"], 3.0),
        ("btn-text-on-accent", c["btn_text"], c["accent"], 4.5),
    ]
    for name, fg, bg, need in pairs:
        ratio = contrast(fg, bg)
        ok = ratio >= need
        _check(checks, f"contrast:{name}", ok,
               f"{ratio}:1 (need {need}:1)")
        if not ok:
            problems.append(f"contrast {name}: {ratio}:1 < {need}:1")

    score = 100
    for chk in checks:
        if chk["ok"]:
            continue
        score -= 15 if chk["name"].startswith("contrast:") else (
            10 if chk["severity"] == "medium" else 8)
    score = max(0, score)
    return {
        "ok": not problems,
        "score": score,
        "preset": preset["title"],
        "preset_key": key,
        "checks": checks,
        "problems": problems,
        "stats": {"files": len(files), "bytes": total},
    }


def render_text(result: dict) -> str:
    mark = "OK" if result["ok"] else "FAIL"
    lines = [f"web audit: {mark} · score {result['score']}/100 · "
             f"preset {result['preset']}"]
    for chk in result["checks"]:
        if not chk["ok"]:
            lines.append(f"  FAIL {chk['name']}: {chk['detail']}")
    if result["ok"]:
        lines.append(f"  {result['stats']['files']} files, "
                     f"{result['stats']['bytes'] / 1024:.1f} KB, offline")
    return "\n".join(lines)
