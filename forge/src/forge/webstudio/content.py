"""Deterministic landing copy. Russian first, English available.

No model calls, no invented facts: the text is generic product copy the
caller can override through the generated `site.json`.
"""
from __future__ import annotations

ICONS = {
    "spark": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2l2.4 7.6L22 12l-7.6 2.4L12 22l-2.4-7.6L2 12l7.6-2.4z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>',
    "layers": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l9 5-9 5-9-5 9-5zM3 13l9 5 9-5M3 18l9 5 9-5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>',
    "bolt": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>',
    "shield": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l7 3v6c0 4.4-2.9 7.7-7 9-4.1-1.3-7-4.6-7-9V6l7-3z" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M9 12l2 2 4-4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
}

COPY = {
    "ru": {
        "lang": "ru",
        "skip": "Перейти к содержанию",
        "nav": [("features", "Возможности"), ("showcase", "Витрина"),
                ("stats", "Цифры")],
        "nav_cta": "Обсудить",
        "eyebrow": "FORGE WEB STUDIO",
        "hero_a": "Сайт, который",
        "hero_b": "движется",
        "lead": "Анимации без библиотек, адаптив без боли, "
                "проверка контраста и JS прямо в генераторе. "
                "Один HTML-файл открывается офлайн.",
        "cta_primary": "Собрать проект",
        "cta_secondary": "Смотреть витрину",
        "panel_title": "forge web audit",
        "panel_rows": [("Контраст", "AA"), ("JS syntax", "ok"),
                       ("Зависимости", "0")],
        "metric": [("97", "", "Lighthouse target"),
                   ("0", "kb", "внешних скриптов"),
                   ("60", "fps", "цель анимаций")],
        "sec_features_kicker": "01 — Возможности",
        "sec_features_title": "Механика, а не картинка",
        "sec_features_lead": "Каждый эффект отключается одной строкой и "
                             "уважает prefers-reduced-motion.",
        "features": [
            ("spark", "Scroll-reveal",
             "Секции появляются по IntersectionObserver, без дёрганья и "
             "пустых transition на каждом элементе."),
            ("layers", "Tilt и parallax",
             "Карточки реагируют на курсор, витрина живёт на скролле — "
             "на Transform, а не на layout."),
            ("bolt", "Частицы и glow",
             "Canvas-частицы и магнитные кнопки добавляются пресетом, "
             "а не тяжёлым фреймворком."),
        ],
        "sec_showcase_kicker": "02 — Витрина",
        "sec_showcase_title": "Собери витрину за минуту",
        "sec_showcase_lead": "Три экрана из коробки: герой, карточки, "
                             "цифры. Меняй пресет — меняется характер.",
        "shots": [
            ("Hero", "Первый экран", "Крупная типографика, градиент, "
                                     "одна понятная кнопка."),
            ("Cards", "Возможности", "Стеклянные карточки, tilt, "
                                     "аккуратные иконки."),
            ("Stats", "Цифры", "Счётчики запускаются только когда "
                               "секция видна."),
        ],
        "sec_stats_kicker": "03 — Цифры",
        "stats": [("6", "", "пресетов"), ("0", "", "зависимостей"),
                  ("100", "", "цель аудита"), ("1", " мин", "до запуска")],
        "cta_title": "Собери свой следующий сайт",
        "cta_text": "forge web new \"Название\" --preset neon --out ./site",
        "cta_button": "Открыть README",
        "footer": "Сгенерировано FORGE Web Studio · работает офлайн",
        "glitch_words": ["SHIP", "BUILD", "ANIMATE"],
        "marquee": "БЕЗ ЗАВИСИМОСТЕЙ · БЕЗ CDN · ТОЛЬКО HTML CSS JS · ",
    },
    "en": {
        "lang": "en",
        "skip": "Skip to content",
        "nav": [("features", "Features"), ("showcase", "Showcase"),
                ("stats", "Numbers")],
        "nav_cta": "Talk to us",
        "eyebrow": "FORGE WEB STUDIO",
        "hero_a": "A site that",
        "hero_b": "moves",
        "lead": "Animations without libraries, responsive without pain, "
                "contrast and JS checks built into the generator. "
                "One HTML file works offline.",
        "cta_primary": "Build a project",
        "cta_secondary": "See the showcase",
        "panel_title": "forge web audit",
        "panel_rows": [("Contrast", "AA"), ("JS syntax", "ok"),
                       ("Dependencies", "0")],
        "metric": [("97", "", "Lighthouse target"),
                   ("0", "kb", "external scripts"),
                   ("60", "fps", "animation target")],
        "sec_features_kicker": "01 — Features",
        "sec_features_title": "Mechanics, not decoration",
        "sec_features_lead": "Every effect can be switched off and respects "
                             "prefers-reduced-motion.",
        "features": [
            ("spark", "Scroll-reveal",
             "Sections appear via IntersectionObserver: no jank, no "
             "transition on every element."),
            ("layers", "Tilt & parallax",
             "Cards react to the pointer, the showcase moves on scroll — "
             "on transforms, never on layout."),
            ("bolt", "Particles & glow",
             "Canvas particles and magnetic buttons come from the preset, "
             "not from a heavy framework."),
        ],
        "sec_showcase_kicker": "02 — Showcase",
        "sec_showcase_title": "Build a showcase in a minute",
        "sec_showcase_lead": "Three screens out of the box: hero, cards, "
                             "numbers. Change the preset, change the mood.",
        "shots": [
            ("Hero", "First screen", "Big type, gradient, one clear "
                                      "call to action."),
            ("Cards", "Features", "Glass cards, tilt, tidy icons."),
            ("Stats", "Numbers", "Counters start only when the section "
                                  "is visible."),
        ],
        "sec_stats_kicker": "03 — Numbers",
        "stats": [("6", "", "presets"), ("0", "", "dependencies"),
                  ("100", "", "audit target"), ("1", " min", "to launch")],
        "cta_title": "Build your next site",
        "cta_text": "forge web new \"Name\" --preset neon --out ./site",
        "cta_button": "Open README",
        "footer": "Generated by FORGE Web Studio · works offline",
        "glitch_words": ["SHIP", "BUILD", "ANIMATE"],
        "marquee": "NO DEPENDENCIES · NO CDN · HTML CSS JS ONLY · ",
    },
}


def copy_for(lang: str) -> dict:
    key = (lang or "ru").strip().lower()
    if key.startswith("en"):
        key = "en"
    else:
        key = "ru"
    return COPY[key]


def normalize_text(value: str, fallback: str) -> str:
    text = " ".join((value or "").split())
    return text[:160] or fallback
