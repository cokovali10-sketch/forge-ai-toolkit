"""Design briefs: from NL description to structured concept + strategy."""
from __future__ import annotations

from dataclasses import dataclass, field


STYLES = ["dark fantasy", "medieval rpg", "futuristic sci-fi", "cyberpunk",
          "minimal premium", "mmorpg", "fantasy mmo", "industrial",
          "magical arcane", "luxury"]
SCREENS = ["shop", "auction", "profile", "inventory", "kit", "mode",
           "stats", "settings", "confirm", "moderation", "server"]
FEATURES = ["search", "sort", "pages", "filters", "buy", "sell", "preview",
            "animation", "localization", "permissions", "economy"]
# Russian synonyms: our users brief in Russian.
RU_SCREENS = {"магазин": "shop", "аукцион": "auction", "профиль": "profile",
              "инвентарь": "inventory", "кит": "kit", "набор": "kit",
              "режим": "mode", "статистика": "stats", "стат": "stats",
              "настройки": "settings", "подтверждение": "confirm",
              "модер": "moderation"}
RU_FEATURES = {"поиск": "search", "сортировка": "sort", "сортировку": "sort",
               "страницы": "pages", "фильтры": "filters", "покупка": "buy",
               "покупку": "buy", "продажа": "sell", "анимации": "animation",
               "анимация": "animation", "локализация": "localization",
               "права": "permissions", "экономика": "economy"}
RU_STYLES = {"тёмное фэнтези": "dark fantasy", "темное фэнтези": "dark fantasy",
             "фэнтези": "fantasy mmo", "киберпанк": "cyberpunk",
             "минимализм": "minimal premium", "люкс": "luxury",
             "средневековье": "medieval rpg", "научная фантастика": "futuristic sci-fi"}


@dataclass
class DesignBrief:
    subject: str
    style: str = "minimal premium"
    screens: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    needs_client_mod: bool = False
    needs_resource_pack: bool = False
    notes: list[str] = field(default_factory=list)


def from_description(text: str) -> DesignBrief:
    """Deterministic NL -> brief. No model calls, keyword-driven."""
    low = text.lower()
    style = next((s for s in STYLES if s in low),
                 next((en for ru, en in RU_STYLES.items() if ru in low),
                      "minimal premium"))
    screens = [s for s in SCREENS if s in low]
    screens += [en for ru, en in RU_SCREENS.items()
                if ru in low and en not in screens]
    if not screens:
        screens = ["shop"]
    features = [f for f in FEATURES if f in low]
    features += [en for ru, en in RU_FEATURES.items()
                 if ru in low and en not in features]
    needs_client = any(k in low for k in
                       ["fullscreen", "free position", "animation", "3d", "custom screen"])
    needs_rp = needs_client or any(k in low for k in
                                   ["texture", "font", "glyph", "icon", "resource"])
    notes = []
    if "auction" in screens and "sort" not in features:
        notes.append("auction without sort requested: added sort by default")
        features.append("sort")
    return DesignBrief(subject=text[:120], style=style, screens=screens,
                       features=features, needs_client_mod=needs_client,
                       needs_resource_pack=needs_rp, notes=notes)
