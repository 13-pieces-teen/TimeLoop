"""Internationalization strings for TimeLoop UI."""

from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    # -- Top-level UI --
    "app_title": {
        "en": "TimeLoop: The Unspeakable Midnight",
        "zh": "TimeLoop: 不可名状的午夜",
    },
    "app_subtitle": {
        "en": "A Lovecraftian time-loop text adventure",
        "zh": "一款克苏鲁风格的时间循环文字冒险",
    },
    "press_new_game": {
        "en": "Press New Game to begin",
        "zh": "点击「新游戏」开始",
    },
    "opening_flavor": {
        "en": "*The salt wind howls outside. Press **New Game** to begin your investigation into Ravenhollow...*",
        "zh": "*咸涩的海风在窗外呼啸。点击 **新游戏** 开始你在雷文霍洛的调查……*",
    },

    # -- Buttons --
    "btn_new_game": {
        "en": "New Game",
        "zh": "新游戏",
    },
    "btn_restart_loop": {
        "en": "Restart Loop",
        "zh": "重启循环",
    },
    "btn_act": {
        "en": "Act",
        "zh": "行动",
    },
    "btn_placeholder": {
        "en": "---",
        "zh": "---",
    },

    # -- Input --
    "input_placeholder": {
        "en": "Or type your own action...",
        "zh": "或输入你想做的事……",
    },

    # -- Status panel --
    "label_status": {
        "en": "Status",
        "zh": "状态",
    },
    "label_inventory": {
        "en": "Inventory",
        "zh": "物品栏",
    },
    "inventory_empty": {
        "en": "(empty)",
        "zh": "（空）",
    },
    "label_npcs": {
        "en": "NPCs",
        "zh": "人物",
    },
    "label_facts": {
        "en": "Facts discovered",
        "zh": "已发现线索",
    },
    "facts_more": {
        "en": "and {n} more",
        "zh": "及其他 {n} 条",
    },

    # -- Info bar --
    "loop_label": {
        "en": "Loop",
        "zh": "循环",
    },
    "memories_label": {
        "en": "memories",
        "zh": "记忆",
    },
    "turn_label": {
        "en": "Turn",
        "zh": "回合",
    },
    "min_left": {
        "en": "min left",
        "zh": "分钟剩余",
    },

    # -- Debug --
    "debug_panel": {
        "en": "Debug Panel",
        "zh": "调试面板",
    },
    "debug_intent": {
        "en": "Intent",
        "zh": "意图",
    },
    "debug_sanity_change": {
        "en": "Sanity Change",
        "zh": "理智变化",
    },
    "debug_consistency": {
        "en": "Consistency Log",
        "zh": "一致性日志",
    },
    "debug_state": {
        "en": "Full State",
        "zh": "完整状态",
    },

    # -- Timeline --
    "timeline_empty": {
        "en": "Press New Game to begin",
        "zh": "点击新游戏开始",
    },

    # -- Language toggle --
    "lang_switch": {
        "en": "EN",
        "zh": "中",
    },

    # -- Event choices fallback --
    "continue": {
        "en": "Continue",
        "zh": "继续",
    },

    # -- Locations --
    "loc_inn": {"en": "Inn", "zh": "旅馆"},
    "loc_church": {"en": "Church", "zh": "教堂"},
    "loc_library": {"en": "Library", "zh": "图书馆"},
    "loc_docks": {"en": "Docks", "zh": "码头"},
    "loc_lighthouse": {"en": "Lighthouse", "zh": "灯塔"},
    "loc_caves": {"en": "Caves", "zh": "洞穴"},
    "loc_cliffs": {"en": "Cliffs", "zh": "悬崖"},
    "loc_town_square": {"en": "Town Square", "zh": "镇广场"},
}

LOCATION_NAMES: dict[str, dict[str, str]] = {
    "inn": {"en": "Inn", "zh": "旅馆"},
    "church": {"en": "Church", "zh": "教堂"},
    "library": {"en": "Library", "zh": "图书馆"},
    "docks": {"en": "Docks", "zh": "码头"},
    "lighthouse": {"en": "Lighthouse", "zh": "灯塔"},
    "caves": {"en": "Caves", "zh": "洞穴"},
    "cliffs": {"en": "Cliffs", "zh": "悬崖"},
    "town_square": {"en": "Town Square", "zh": "镇广场"},
}


def t(key: str, lang: str = "en", **kwargs: str) -> str:
    """Get a translated string. Falls back to English if key/lang is missing."""
    entry = STRINGS.get(key, {})
    text = entry.get(lang, entry.get("en", key))
    for k, v in kwargs.items():
        text = text.replace(f"{{{k}}}", str(v))
    return text


def loc_name(location_id: str, lang: str = "en") -> str:
    """Get localized location name."""
    entry = LOCATION_NAMES.get(location_id, {})
    return entry.get(lang, location_id.replace("_", " ").title())
