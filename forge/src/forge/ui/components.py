"""Component model + REAL validators (no screenshots needed).

Inventory realities enforced: 54 slots, nav row, no overlaps, readable text,
contrast math (WCAG-ish relative luminance), clicable zones.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Component:
    kind: str  # panel|button|label|item_slot|search|pagination|modal|...
    slots: list[int] = field(default_factory=list)
    text: str = ""
    action: str = ""  # click action id, "" = decorative
    states: list[str] = field(default_factory=lambda: ["normal"])


def _luminance(argb: int) -> float:
    def ch(v: int) -> float:
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r = ch((argb >> 16) & 0xFF)
    g = ch((argb >> 8) & 0xFF)
    b = ch(argb & 0xFF)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: int, bg: int) -> float:
    a, b = _luminance(fg), _luminance(bg)
    lo, hi = min(a, b), max(a, b)
    return (hi + 0.05) / (lo + 0.05)


def validate_inventory(screen: dict) -> list[str]:
    """screen: {title, size, components:[{kind,slots,text,action,states}]}.
    Returns error strings (empty = valid)."""
    errs: list[str] = []
    size = screen.get("size", 54)
    if size not in (9, 18, 27, 36, 45, 54):
        errs.append(f"bad inventory size {size} (must be 9..54 step 9)")
        return errs
    if len(screen.get("title", "")) > 32:
        errs.append("title longer than 32 chars will clip")
    seen: dict[int, str] = {}
    has_nav = False
    for c in screen.get("components", []):
        kind = c.get("kind", "?")
        for s in c.get("slots", []):
            if not 0 <= s < size:
                errs.append(f"{kind}: slot {s} outside 0..{size - 1}")
            elif s in seen:
                errs.append(f"slot {s} shared by {seen[s]} and {kind}")
            else:
                seen[s] = kind
        if kind in ("button", "pagination") and not c.get("action"):
            errs.append(f"{kind} at {c.get('slots')}: clickable without action")
        if kind == "pagination":
            has_nav = True
        text = c.get("text", "")
        if kind == "label" and len(text) > 40:
            errs.append(f"label too long ({len(text)} chars): {text[:30]!r}")
    content = [s for s, k in seen.items() if k == "item_slot"]
    if content and not has_nav and len(content) > 28:
        errs.append(f"{len(content)} item slots without pagination")
    return errs


def validate_contrast(fg: int, bg: int, where: str) -> list[str]:
    r = contrast(fg, bg)
    if r < 3.0:
        return [f"{where}: contrast {r:.1f} < 3.0 unreadable"]
    if r < 4.5:
        return [f"{where}: contrast {r:.1f} < 4.5 prefer brighter text"]
    return []
