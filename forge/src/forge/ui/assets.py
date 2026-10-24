"""Programmatic asset production (PIL). Real PNGs, manifests, validation.

Generates: panel background, button states (normal/hover/disabled),
frame border, divider, search box. No placeholders: every file is written
pixels and re-opened to verify.
"""
from __future__ import annotations

import json
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError as _exc:  # pragma: no cover - depends on environment
    raise ImportError(
        "Pillow is required for asset generation: pip install 'forge-core[ui]'"
    ) from _exc


def _argb(hexstr: str) -> tuple[int, int, int, int]:
    h = hexstr.lstrip("#")
    if len(h) == 6:
        h = "FF" + h
    a = int(h[0:2], 16)
    return int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16), a


def _save(img: Image.Image, path: Path) -> dict:
    img.save(path, "PNG")
    with Image.open(path) as check:
        check.load()
        w, h = check.size
        mode = check.mode
    if w <= 0 or h <= 0:
        raise ValueError(f"empty image: {path}")
    return {"path": str(path), "size": [w, h], "mode": mode,
            "bytes": path.stat().st_size}


def panel(system: dict, out: Path, w: int = 256, h: int = 128) -> dict:
    bg = _argb(system["colors"]["panel"])
    border = _argb(system["colors"]["border"])
    hi = _argb(system["colors"].get("accent_bright", "#E03040"))
    img = Image.new("RGBA", (w, h), bg)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, h - 1], outline=border, width=2)
    d.line([2, 2, w - 3, 2], fill=hi[:3] + (110,), width=1)  # glass highlight
    return _save(img, out)


def button(system: dict, out: Path, state: str = "normal",
           w: int = 120, h: int = 20) -> dict:
    accent = _argb(system["colors"]["accent"])
    border = _argb(system["colors"]["border"])
    base = {"normal": accent, "hover": _argb(system["colors"]["accent_bright"]),
            "disabled": (46, 46, 46, 255)}[state]
    img = Image.new("RGBA", (w, h), base)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, h - 1], outline=border, width=1)
    d.line([1, 1, w - 2, 1], fill=(255, 255, 255, 70), width=1)
    return _save(img, out)


def divider(system: dict, out: Path, w: int = 200) -> dict:
    border = _argb(system["colors"]["border"])
    img = Image.new("RGBA", (w, 3), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line([0, 1, w - 1, 1], fill=border, width=1)
    d.line([0, 0, w - 1, 0], fill=(255, 255, 255, 40), width=1)
    return _save(img, out)


def build_pack(system: dict, out_dir: str | Path, mc: str = "1.21.11") -> dict:
    """Generates a themed asset set + manifest. Returns manifest dict."""
    out = Path(out_dir)
    (out / "textures").mkdir(parents=True, exist_ok=True)
    assets = []
    assets.append({"id": "panel", "use": "menu background",
                   **panel(system, out / "textures" / "panel.png")})
    for state in ("normal", "hover", "disabled"):
        assets.append({"id": f"button_{state}", "use": "button state",
                       **button(system, out / "textures" / f"button_{state}.png",
                                state)})
    assets.append({"id": "divider", "use": "section separator",
                   **divider(system, out / "textures" / "divider.png")})
    manifest = {"pack": system["name"], "minecraft": mc, "assets": [
        {**a, "format": "PNG", "source": "forge-asset-pipeline",
         "license": "generated, free to use"} for a in assets]}
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest

def pack_mcmeta(description: str, out_dir: str | Path, pack_format: int = 48) -> str:
    """Writes pack.mcmeta so the folder is a loadable resource pack."""
    p = Path(out_dir) / "pack.mcmeta"
    p.write_text(json.dumps({"pack": {"pack_format": pack_format,
                                      "description": description}},
                            ensure_ascii=False, indent=2), encoding="utf-8")
    return str(p)


def import_graphics(src: str | Path, out_dir: str | Path, system: dict,
                    max_side: int = 256, max_kb: int = 512) -> dict:
    """Validates external PNGs into the pack: opens, checks, downscales,
    records manifest entries. Rejects unreadable/oversize files honestly."""
    from . import system as _sys
    if _sys.validate(system):
        raise ValueError("invalid design system")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    accepted: list[dict] = []
    rejected: list[dict] = []
    for f in sorted(Path(src).glob("*.png")):
        try:
            with Image.open(f) as img:
                img.load()
                w, h = img.size
                if img.mode not in ("RGBA", "RGB", "P", "L", "LA"):
                    raise ValueError(f"mode {img.mode}")
                if max(w, h) > max_side:
                    img = img.convert("RGBA")
                    img.thumbnail((max_side, max_side), Image.LANCZOS)
                    w, h = img.size
                else:
                    img = img.convert("RGBA")
                dst = out / f.name
                img.save(dst, "PNG")
                if dst.stat().st_size > max_kb * 1024:
                    dst.unlink(missing_ok=True)
                    raise ValueError(f">{max_kb}KB after convert")
                accepted.append({"id": f.stem, "size": [w, h],
                                 "bytes": dst.stat().st_size})
        except Exception as e:
            rejected.append({"file": f.name,
                             "reason": f"{type(e).__name__}: {e}"[:200]})
    return {"accepted": accepted, "rejected": rejected}


def _to_argb(value: str | int) -> int:
    if isinstance(value, int):
        return value
    h = value.lstrip("#")
    if len(h) == 6:
        h = "FF" + h
    return int(h, 16)


def iterate(system: dict, out_dir: str | Path, rounds: int = 3) -> dict:
    """Deterministic visual iteration WITHOUT screenshots: generates pack
    variants (opacity steps), scores each with component validators
    (contrast of text-on-panel + button-on-panel), keeps the best.
    Returns winner + score log. Honest scope documented in ui-engine.md."""
    from . import components as _c
    out = Path(out_dir)
    base_panel = _to_argb(system["colors"]["panel"]) & 0xFFFFFF
    text = _to_argb(system["colors"]["text"])
    btn = _to_argb(system["colors"]["accent"])
    log = []
    best = None
    for i in range(max(1, rounds)):
        alpha = min(0xFF, 0xB0 + i * 0x10)
        bg = (alpha << 24) | base_panel
        errs = _c.validate_contrast(text, bg, f"round-{i}-text")
        errs += _c.validate_contrast(0xFFFFFFFF, btn, f"round-{i}-btn")
        score = 100 - 25 * len(errs)
        log.append({"round": i, "alpha": alpha, "errors": errs, "score": score})
        if best is None or score > best["score"]:
            best = log[-1]
    out.mkdir(parents=True, exist_ok=True)
    (out / "iteration.json").write_text(
        json.dumps({"log": log, "best": best}, indent=2), encoding="utf-8")
    return {"best": best, "log": log, "out": str(out)}
