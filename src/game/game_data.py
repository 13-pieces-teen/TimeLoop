"""Pure data tables extracted from GameEngine to reduce class size."""

from __future__ import annotations

AUTO_TRUST_PER_INTERACTION = 1
KNOWLEDGE_TRUST_BONUS = 25
KNOWLEDGE_WRONG_NPC_PENALTY = -8
TIME_PER_TURN = 15

FACT_TRUST_MAP: dict[str, dict[str, int]] = {
    "martha": {
        "elias_stayed_at_inn": 5,
        "thomas_holloway_heard_whispers": 10,
        "thomas_holloway_missing_six_months": 5,
        "multiple_people_have_disappeared": 5,
    },
    "morrison": {
        "ritual_happens_every_30_years": 15,
        "elias_found_alternative_method": 10,
        "morrison_performed_last_ritual": 10,
        "ritual_requires_sacrifice": 5,
    },
    "eleanor": {
        "elias_stayed_at_inn": 5,
        "morrison_locked_elias_in_lighthouse": 10,
        "eleanor_helped_elias": 5,
        "elias_discovered_lens_ritual": 10,
    },
    "silas": {
        "entity_sleeps_beneath_bay": 10,
        "thomas_holloway_heard_whispers": 5,
        "entity_is_dreaming_not_evil": 10,
        "silas_witnessed_the_entity": 5,
    },
}

HALLUCINATION_NARRATIONS: dict[str, list[str]] = {
    "en": [
        "You reach for something that isn't there. The world tilts, steadies, and you're exactly where you started. Time has passed.",
        "The whispers coalesce into a shape, then dissolve. You blink. Minutes have vanished.",
        "You follow the pull — but there's nothing. Just the wind, the salt, and the growing certainty that you are being watched.",
    ],
    "zh": [
        "你伸手去够一个不存在的东西。世界倾斜，又恢复稳定，你还在原地。时间已经过去了。",
        "低语凝聚成某种形状，随即消散。你眨了眨眼。几分钟凭空消失了。",
        "你循着那股引力走去——但什么都没有。只有风、盐味，以及越来越强烈的被注视感。",
    ],
}

HALLUCINATION_CHOICES: dict[str, list[dict]] = {
    "en": [
        {"id": "follow_whispers", "text": "Follow the whispers toward the sea", "sanity_cost": -8},
        {"id": "open_nonexistent_door", "text": "Open the door that wasn't there before", "sanity_cost": -10},
        {"id": "answer_the_singing", "text": "Answer the singing from below", "sanity_cost": -12},
        {"id": "touch_the_symbol", "text": "Trace the symbol burned into your vision", "sanity_cost": -6},
        {"id": "speak_to_shadow", "text": "Address the figure in the corner of your eye", "sanity_cost": -8},
        {"id": "drink_the_seawater", "text": "The sea looks like it's offering you something", "sanity_cost": -15},
    ],
    "zh": [
        {"id": "follow_whispers", "text": "循着低语走向大海", "sanity_cost": -8},
        {"id": "open_nonexistent_door", "text": "打开那扇之前不存在的门", "sanity_cost": -10},
        {"id": "answer_the_singing", "text": "回应来自深处的歌声", "sanity_cost": -12},
        {"id": "touch_the_symbol", "text": "描摹灼烧在视野中的符文", "sanity_cost": -6},
        {"id": "speak_to_shadow", "text": "对眼角的人影说话", "sanity_cost": -8},
        {"id": "drink_the_seawater", "text": "大海似乎在向你递出什么", "sanity_cost": -15},
    ],
}

HALLUCINATION_IDS: set[str] = {
    c["id"] for pool in HALLUCINATION_CHOICES.values() for c in pool
}

NARRATIVE_HOOKS: list[dict] = [
    {
        "requires_fact": "elias_stayed_at_inn",
        "target_location": "library",
        "en": "Martha mentioned Elias spent long hours at the library, poring over old records... what was he looking for?",
        "zh": "玛莎提到伊莱亚斯曾在图书馆里泡上好几个小时，翻阅陈旧的档案……他在找什么？",
    },
    {
        "requires_fact": "thomas_holloway_heard_whispers",
        "target_location": "docks",
        "en": "Thomas heard whispers from the sea. The docks might hold traces of what drew him to the water.",
        "zh": "托马斯听到了来自大海的低语。码头或许留有将他引向海水的痕迹。",
    },
    {
        "requires_fact": "ritual_happens_every_30_years",
        "target_location": "church",
        "en": "A thirty-year cycle... The church records might document previous occurrences.",
        "zh": "三十年的周期……教堂的记录里也许记载了之前的事件。",
    },
    {
        "requires_fact": "entity_sleeps_beneath_bay",
        "target_npc": "silas",
        "en": "Something sleeps beneath the bay. Old Silas, who has spent a lifetime on these waters, might know more.",
        "zh": "有什么东西沉睡在海湾之下。在这片海域生活了一辈子的老西拉斯，或许知道更多。",
    },
    {
        "requires_fact": "morrison_locked_elias_in_lighthouse",
        "target_npc": "eleanor",
        "en": "Morrison locked Elias in the lighthouse... Eleanor worked with Elias. Does she know what really happened?",
        "zh": "莫里森把伊莱亚斯锁在了灯塔里……埃莉诺曾和伊莱亚斯共事。她知道真相吗？",
    },
    {
        "requires_fact": "eleanor_helped_elias",
        "target_npc": "morrison",
        "en": "Eleanor gave Elias access to forbidden knowledge. What does Morrison think about that?",
        "zh": "埃莉诺让伊莱亚斯接触了禁忌知识。莫里森对此怎么看？",
    },
    {
        "requires_fact": "morrison_performed_last_ritual",
        "target_npc": "morrison",
        "en": "Morrison's hands have blood on them — Arthur Crane's. The weight of that secret must be crushing him.",
        "zh": "莫里森的双手沾着鲜血——亚瑟·克莱恩的。这个秘密的重量一定快要压垮他了。",
    },
    {
        "requires_fact": "silas_witnessed_the_entity",
        "target_location": "docks",
        "en": "Silas saw the water open like a door. What lies beyond that threshold?",
        "zh": "西拉斯看到水面像一扇门一样打开。门的那一边是什么？",
    },
]

LOCATION_KEYWORDS: list[tuple[str, list[str]]] = [
    ("lighthouse", ["lighthouse", "灯塔"]),
    ("library",    ["library", "图书馆", "书馆"]),
    ("church",     ["church", "教堂", "圣安德鲁", "st. andrew"]),
    ("docks",      ["dock", "docks", "pier", "码头", "栈桥", "渔港"]),
    ("caves",      ["cave", "caves", "洞穴", "山洞", "洞口"]),
    ("inn",        ["inn", "旅馆", "旅店", "hotel"]),
]

ALL_EXPLORABLE_LOCATIONS = ["inn", "library", "church", "docks"]

# ---------------------------------------------------------------------------
# Ambient sanity drain — hidden from player, applied silently each turn.
#
# Design:  drain = time_phase_base + location_modifier
#
# The game day runs 8:00 PM → 12:00 AM (0–240 minutes).
# Three phases model rising dread as midnight approaches:
#   Dusk   (8:00–9:30 PM, min 0–89):   town feels merely unsettling
#   Night  (9:30–11:00 PM, min 90–179): darkness deepens, whispers grow
#   Witching (11:00 PM+, min 180+):     reality frays, drain surges
#
# Location modifier adds danger flavour:
#   inn (warmth/normalcy) → 0  |  library/church → −1
#   docks → −2  |  lighthouse → −3  |  caves → −4
# ---------------------------------------------------------------------------

_PHASE_BASE: list[tuple[int, int]] = [
    (90,  -1),   # 8:00 PM – 9:30 PM
    (180, -2),   # 9:30 PM – 11:00 PM
    (999, -4),   # 11:00 PM – midnight
]

LOCATION_DANGER: dict[str, int] = {
    "inn":        0,
    "library":   -1,
    "church":    -1,
    "docks":     -2,
    "lighthouse": -3,
    "caves":     -4,
}


def compute_ambient_sanity_drain(time_minutes: int, location: str) -> int:
    """Return the hidden per-turn sanity drain (always <= 0).

    The value is NOT surfaced to the player via ``sanity_delta``.
    """
    base = -1
    for threshold, drain in _PHASE_BASE:
        if time_minutes < threshold:
            base = drain
            break

    modifier = LOCATION_DANGER.get(location, -1)
    return base + modifier
