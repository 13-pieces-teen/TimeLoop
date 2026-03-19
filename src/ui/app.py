from __future__ import annotations

import random
from pathlib import Path

import gradio as gr

from src.game.engine import GameEngine, TurnResult
from src.game.loop_manager import LoopManager
from src.state.game_state import SANITY_EFFECTS
from src.ui.i18n import t, loc_name

SANITY_COLORS = {
    "lucid": "#4ade80",
    "uneasy": "#facc15",
    "distorted": "#f97316",
    "madness": "#ef4444",
}

THEME = gr.themes.Base(
    primary_hue=gr.themes.colors.indigo,
    secondary_hue=gr.themes.colors.slate,
    neutral_hue=gr.themes.colors.slate,
    font=gr.themes.GoogleFont("Crimson Text"),
    font_mono=gr.themes.GoogleFont("JetBrains Mono"),
).set(
    body_background_fill="#0b0e17",
    body_background_fill_dark="#0b0e17",
    body_text_color="#c9d1d9",
    body_text_color_dark="#c9d1d9",
    block_background_fill="#131829",
    block_background_fill_dark="#131829",
    block_border_color="#1e2a4a",
    block_border_color_dark="#1e2a4a",
    block_label_text_color="#8892b0",
    block_label_text_color_dark="#8892b0",
    block_title_text_color="#ccd6f6",
    block_title_text_color_dark="#ccd6f6",
    input_background_fill="#0d1117",
    input_background_fill_dark="#0d1117",
    input_border_color="#1e2a4a",
    input_border_color_dark="#1e2a4a",
    button_primary_background_fill="#1a3a5c",
    button_primary_background_fill_dark="#1a3a5c",
    button_primary_background_fill_hover="#234b73",
    button_primary_background_fill_hover_dark="#234b73",
    button_primary_text_color="#ccd6f6",
    button_primary_text_color_dark="#ccd6f6",
    button_secondary_background_fill="#161b2e",
    button_secondary_background_fill_dark="#161b2e",
    button_secondary_background_fill_hover="#1e2a4a",
    button_secondary_background_fill_hover_dark="#1e2a4a",
    button_secondary_text_color="#8892b0",
    button_secondary_text_color_dark="#8892b0",
    button_secondary_border_color="#1e2a4a",
    button_secondary_border_color_dark="#1e2a4a",
)

def _load_static_assets() -> tuple[str, str]:
    """Load all CSS and JS from external files at import time."""
    _ui_dir = Path(__file__).parent
    styles_dir = _ui_dir / "styles"
    css_parts: list[str] = []
    for name in ("base", "status", "timeline", "narrative", "sanity", "mobius"):
        css_file = styles_dir / f"{name}.css"
        if css_file.exists():
            css_parts.append(css_file.read_text(encoding="utf-8"))
    css = "\n".join(css_parts)

    js_file = _ui_dir / "scripts" / "typewriter.js"
    js = js_file.read_text(encoding="utf-8") if js_file.exists() else ""
    return css, js


CSS, TYPEWRITER_JS = _load_static_assets()


# =====================================================================
# Formatters (all accept lang)
# =====================================================================

SANITY_FLAVOR = {
    "lucid": {
        "en": "A chill passes through you.",
        "zh": "一阵寒意穿透了你。",
    },
    "uneasy": {
        "en": "The edges of your vision blur momentarily.",
        "zh": "你视野的边缘短暂地模糊了。",
    },
    "distorted": {
        "en": "Something inside you unravels a little further.",
        "zh": "你内心深处有什么东西又崩解了一些。",
    },
    "madness": {
        "en": "You can no longer tell if the screaming is yours.",
        "zh": "你已经分不清那尖叫声是不是你自己发出的。",
    },
}


def format_narration(result: TurnResult, lang: str = "en", sanity_level: str = "lucid") -> str:
    parts = []
    if result.event_triggered:
        parts.append(f"### {result.event_triggered}\n\n")
    parts.append(result.narration or "")
    if result.dialogue_speaker and result.dialogue_text:
        parts.append(
            f'\n\n---\n\n'
            f'**{result.dialogue_speaker}:**\n\n'
            f'*"{result.dialogue_text}"*'
        )

    delta = result.sanity_delta
    if delta and delta != 0:
        flavor = SANITY_FLAVOR.get(sanity_level, SANITY_FLAVOR["lucid"])
        text = flavor.get(lang, flavor["en"])
        san_label = "理智" if lang == "zh" else "SAN"
        parts.append(f"\n\n*{text} ({san_label} {delta:+d})*")

    return "".join(parts)


ALL_LOCATION_IDS = ["inn", "library", "church", "docks", "lighthouse", "caves"]


def format_info_bar(engine: GameEngine, lang: str = "en") -> str:
    if not engine.game_state:
        return f'<div class="info-bar san-lucid"><span>{t("press_new_game", lang)}</span></div>'
    gs = engine.game_state
    lm = engine.loop_memory

    sanity = gs.sanity
    level = gs.sanity_level
    fx = SANITY_EFFECTS.get(level, SANITY_EFFECTS["lucid"])
    jitter = fx["display_jitter"]

    displayed_sanity = sanity
    if jitter > 0:
        displayed_sanity = sanity + random.randint(-jitter, jitter)
        displayed_sanity = max(-5, min(115, displayed_sanity))

    color = SANITY_COLORS.get(level, "#fff")
    filled = max(0, min(20, int(displayed_sanity / 5)))
    bar = "\u2588" * filled + "\u2591" * (20 - filled)
    level_label = t(f"san_{level}", lang)

    loop_info = f"{t('loop_label', lang)} #{gs.loop_count}"
    if lm.total_loops > 0:
        loop_info += f" ({t('memories_label', lang)}: {lm.total_loops})"

    time_str = gs.current_time_str
    min_left = gs.minutes_until_midnight
    if level == "madness":
        min_left = min_left + random.randint(-30, 30)
        time_str = gs.current_time_str.replace(":", f":{random.randint(0, 5)}", 1) if random.random() < 0.3 else time_str

    location = loc_name(gs.location, lang)
    if level == "madness" and random.random() < 0.25:
        other_locs = [lid for lid in ALL_LOCATION_IDS if lid != gs.location]
        location = loc_name(random.choice(other_locs), lang)

    return (
        f'<div class="info-bar san-{level}">'
        f'<div class="sanity-section">'
        f'<span class="san-value" style="color:{color}; font-weight:600;">{bar} {displayed_sanity}/100 [{level_label}]</span>'
        f'</div>'
        f'<div class="meta-section">'
        f'<span class="meta-time">{time_str} ({min_left} {t("min_left", lang)})</span> '
        f'&nbsp;|&nbsp; {loop_info} &nbsp;|&nbsp; {t("turn_label", lang)} {gs.turn} '
        f'&nbsp;|&nbsp; {location}'
        f'</div>'
        f'</div>'
    )


TRUST_EVENT_THRESHOLDS = [25, 30, 40, 50, 70, 90]

TRUST_HINTS_ZH = {
    "close": "似乎快要对你说什么了",
    "warming": "正在慢慢信任你",
}
TRUST_HINTS_EN = {
    "close": "seems about to tell you something",
    "warming": "is warming up to you",
}

TRUST_DESCRIPTIONS = {
    "en": [
        (0, "Stranger — guarded"),
        (20, "Acquaintance — willing to talk"),
        (40, "Cautious ally — shares some secrets"),
        (60, "Trusted — confides deeper truths"),
        (80, "Deep bond — entrusts their fate to you"),
    ],
    "zh": [
        (0, "陌生人——心存戒备"),
        (20, "点头之交——愿意交谈"),
        (40, "谨慎的同伴——分享了一些秘密"),
        (60, "信任——吐露更深的真相"),
        (80, "深厚羁绊——将命运托付于你"),
    ],
}

NPC_COLORS = {
    "martha": "#d4a574",
    "morrison": "#8b9dc3",
    "eleanor": "#7eb8a8",
    "silas": "#a0a0a0",
}

MYSTERY_PAIRS = [
    ("morrison_locked_elias_in_lighthouse", "elias_found_alternative_method",
     "Why did Morrison lock Elias in the lighthouse?", "莫里森为什么把伊莱亚斯锁在灯塔里？"),
    ("thomas_holloway_heard_whispers", "martha_hears_whispers_too",
     "What is the source of the whispers from the sea?", "大海中低语的来源是什么？"),
    ("ritual_happens_every_30_years", "elias_found_alternative_method",
     "Is there a way to break the thirty-year cycle?", "有没有办法打破三十年的循环？"),
    ("entity_sleeps_beneath_bay", "entity_is_dreaming_not_evil",
     "What is the true nature of the entity beneath the bay?", "海湾之下存在的真正本质是什么？"),
]


def _get_trust_hint(trust: int, lang: str) -> str:
    hints = TRUST_HINTS_ZH if lang == "zh" else TRUST_HINTS_EN
    next_threshold = next((th for th in TRUST_EVENT_THRESHOLDS if th > trust), None)
    if next_threshold is None:
        return ""
    gap = next_threshold - trust
    if gap <= 10:
        return hints["close"]
    if gap <= 20:
        return hints["warming"]
    return ""


def _get_trust_description(trust: int, lang: str) -> str:
    descs = TRUST_DESCRIPTIONS.get(lang, TRUST_DESCRIPTIONS["en"])
    result = descs[0][1]
    for threshold, desc in descs:
        if trust >= threshold:
            result = desc
    return result


def _trust_dots_html(trust: int) -> str:
    """Render 5 dots representing 0-100 trust (each dot = 20)."""
    filled = min(5, trust // 20)
    if trust >= 80:
        cls = "filled-gold"
    elif trust >= 50:
        cls = "filled-green"
    elif trust >= 20:
        cls = "filled-blue"
    else:
        cls = "filled-gray"
    dots = []
    for i in range(5):
        c = cls if i < filled else ""
        dots.append(f'<span class="sp-dot {c}"></span>')
    return "".join(dots)


FALSE_MEMORIES = {
    "en": [
        "Elias left a second letter — hidden under the floorboards",
        "The lighthouse lamp was lit on the night Thomas vanished",
        "Morrison was seen at the docks at 3 AM, carrying a bundle",
        "There is a fifth NPC you keep forgetting about",
        "You've been here before. Not in a loop. Before that.",
    ],
    "zh": [
        "伊莱亚斯留了第二封信——藏在地板下面",
        "托马斯失踪那晚灯塔的灯亮着",
        "有人看到莫里森凌晨三点在码头，抱着一个包裹",
        "有第五个NPC，你一直在遗忘",
        "你以前来过这里。不是循环。在那之前。",
    ],
}


def _corrupt_fact(text: str, san_level: str, lang: str) -> str:
    """Deterministically corrupt a fact string based on sanity level."""
    if san_level in ("lucid", "uneasy"):
        return text
    fx = SANITY_EFFECTS.get(san_level, SANITY_EFFECTS["lucid"])
    seed = hash(text) & 0xFFFFFFFF
    rng = random.Random(seed)
    if rng.random() > fx["fact_corrupt"]:
        return text

    words = text.split()
    if not words:
        return text

    if san_level == "madness":
        glitch_chars = "░▒▓█▌▐▀▄"
        n_corrupt = max(1, len(words) // 3)
        for _ in range(n_corrupt):
            idx = rng.randrange(len(words))
            w = words[idx]
            replacement = "".join(rng.choice(glitch_chars) for _ in range(len(w)))
            words[idx] = replacement
    else:
        idx = rng.randrange(len(words))
        w = words[idx]
        words[idx] = w[::-1] if len(w) > 3 else "█" * len(w)

    return " ".join(words)


def format_status(engine: GameEngine, lang: str = "en") -> str:
    if not engine.game_state:
        return ""
    gs = engine.game_state
    desc = engine.descriptions
    item_descs = desc.get("items", {})
    fact_descs = desc.get("facts", {})
    cat_descs = desc.get("categories", {})

    html_parts = ['<div class="status-html">']

    # --- Items ---
    inv_label = t("label_inventory", lang)
    html_parts.append(f'<div class="sp-section"><div class="sp-header">{inv_label}</div>')
    if gs.inventory:
        for item_id in gs.inventory:
            info = item_descs.get(item_id, {})
            icon = info.get("icon", "&#8226;")
            name = info.get(lang, info.get("en", item_id.replace("_", " ")))
            html_parts.append(
                f'<div class="sp-item">'
                f'<span class="sp-item-icon">{icon}</span>'
                f'<span class="sp-item-name">{name}</span>'
                f'</div>'
            )
    else:
        empty = t("inventory_empty", lang)
        html_parts.append(f'<div class="sp-empty">{empty}</div>')
    html_parts.append('</div>')

    # --- NPCs (journal style) ---
    npc_label = t("label_npcs", lang)
    html_parts.append(f'<div class="sp-section"><div class="sp-header">{npc_label}</div>')

    for npc_id, npc in gs.characters.items():
        if not npc.alive:
            continue
        is_here = npc.location == gs.location
        trust_desc = _get_trust_description(npc.trust, lang)
        hint = _get_trust_hint(npc.trust, lang)
        dots = _trust_dots_html(npc.trust)
        name_color = NPC_COLORS.get(npc_id, "#ccd6f6")
        name_style = "" if is_here else ' style="color:#6b7280;"'

        html_parts.append(f'<div class="sp-npc">')
        html_parts.append(
            f'<div class="sp-npc-row">'
            f'<span class="sp-npc-name"{name_style}>'
            f'<span style="color:{name_color};">&#9679;</span> {npc.name}'
            f'</span>'
            f'<div class="sp-dots">{dots}</div>'
            f'</div>'
        )
        html_parts.append(f'<div class="journal-trust-desc">{trust_desc}</div>')
        if hint:
            html_parts.append(f'<div class="sp-npc-hint">{hint}</div>')
        if not is_here:
            loc_label = loc_name(npc.location, lang)
            html_parts.append(f'<div class="sp-npc-loc">@ {loc_label}</div>')
        html_parts.append('</div>')

    html_parts.append('</div>')

    # --- Facts (journal notes) — corrupted at low sanity ---
    san_level = gs.sanity_level
    facts_label = "调查手记" if lang == "zh" else "Investigation Notes"
    if san_level == "madness":
        facts_label = "░调░查░手░记░" if lang == "zh" else "I̷n̷v̷e̷s̷t̷i̷g̷a̷t̷i̷o̷n̷ Notes"
    html_parts.append(f'<div class="sp-section"><div class="sp-header">{facts_label}</div>')
    if gs.discovered_facts:
        by_cat: dict[str, list[str]] = {}
        for fact_id in gs.discovered_facts:
            info = fact_descs.get(fact_id, {})
            cat = info.get("category", "other")
            by_cat.setdefault(cat, []).append(fact_id)

        for cat_id, fact_ids in by_cat.items():
            cat_info = cat_descs.get(cat_id, {})
            cat_label = cat_info.get(lang, cat_info.get("en", cat_id))
            html_parts.append(f'<div class="sp-cat-label">{cat_label}</div>')
            for fid in fact_ids:
                info = fact_descs.get(fid, {})
                text = info.get(lang, info.get("en", fid.replace("_", " ")))
                text = _corrupt_fact(text, san_level, lang)
                html_parts.append(f'<div class="sp-fact">{text}</div>')

        if san_level == "madness":
            false_pool = FALSE_MEMORIES.get(lang, FALSE_MEMORIES["en"])
            n_false = min(2, len(false_pool))
            for fm in random.sample(false_pool, n_false):
                html_parts.append(f'<div class="sp-fact" style="color:#a855f7;">{fm}</div>')
    else:
        empty = "尚无线索" if lang == "zh" else "No clues yet"
        html_parts.append(f'<div class="sp-empty">{empty}</div>')

    # --- Unsolved Mysteries ---
    mysteries = []
    for fact_a, fact_b, mystery_en, mystery_zh in MYSTERY_PAIRS:
        if fact_a in gs.discovered_facts and fact_b not in gs.discovered_facts:
            mysteries.append(mystery_zh if lang == "zh" else mystery_en)

    if mysteries:
        mystery_header = "未解之谜" if lang == "zh" else "Unsolved"
        html_parts.append(f'<div class="sp-cat-label" style="color:#eab308;">{mystery_header}</div>')
        for m in mysteries[:3]:
            html_parts.append(f'<div class="journal-mystery">{m}</div>')

    html_parts.append('</div>')
    html_parts.append('</div>')
    return "".join(html_parts)


MAP_NODES = {
    "inn":        (120, 75),
    "library":    (30, 75),
    "docks":      (210, 75),
    "church":     (120, 140),
    "lighthouse": (210, 15),
    "caves":      (120, 200),
}
MAP_EDGES = [
    ("inn", "library"), ("inn", "docks"), ("inn", "church"),
    ("church", "caves"), ("docks", "lighthouse"),
]
LOCKED_LOCATIONS = {"caves", "lighthouse"}


def format_location_map(engine: GameEngine, lang: str = "en") -> str:
    if not engine.game_state:
        return ""
    gs = engine.game_state
    visited = gs.flags.get("_visited_locations", [])
    if not isinstance(visited, list):
        visited = []

    svg_parts = ['<svg viewBox="0 0 240 220" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;">']

    for a, b in MAP_EDGES:
        ax, ay = MAP_NODES[a]
        bx, by = MAP_NODES[b]
        svg_parts.append(
            f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" '
            f'stroke="#1e2a4a" stroke-width="1.5" stroke-dasharray="4 3"/>'
        )

    for loc_id, (cx, cy) in MAP_NODES.items():
        is_current = loc_id == gs.location
        is_visited = loc_id in visited
        is_locked = loc_id in LOCKED_LOCATIONS and not is_visited

        from src.ui.i18n import loc_name as _ln
        label = _ln(loc_id, lang)

        npc_here = [n.name for n in gs.characters.values()
                    if n.location == loc_id and n.alive]

        if is_current:
            svg_parts.append(
                f'<circle cx="{cx}" cy="{cy}" r="14" fill="#3b82f6" opacity="0.15"/>'
                f'<circle cx="{cx}" cy="{cy}" r="8" fill="#3b82f6">'
                f'<animate attributeName="r" values="8;10;8" dur="2s" repeatCount="indefinite"/>'
                f'</circle>'
            )
            text_cls = "current-loc"
        elif is_locked:
            svg_parts.append(
                f'<circle cx="{cx}" cy="{cy}" r="7" fill="none" stroke="#374151" stroke-width="1.5" stroke-dasharray="3 2"/>'
                f'<text x="{cx}" y="{cy+3}" text-anchor="middle" font-size="8" fill="#374151">&#x1f512;</text>'
            )
            text_cls = "locked-loc"
        elif is_visited:
            svg_parts.append(
                f'<circle cx="{cx}" cy="{cy}" r="7" fill="#2dd4bf" opacity="0.6"/>'
            )
            text_cls = "visited-loc"
        else:
            svg_parts.append(
                f'<circle cx="{cx}" cy="{cy}" r="7" fill="none" stroke="#4b5563" stroke-width="1.5"/>'
            )
            text_cls = ""

        svg_parts.append(
            f'<text x="{cx}" y="{cy - 14}" text-anchor="middle" class="{text_cls}">{label}</text>'
        )

        if npc_here and not is_locked:
            npc_label = ", ".join(npc_here[:2])
            svg_parts.append(
                f'<text x="{cx}" y="{cy + 22}" text-anchor="middle" '
                f'font-size="7" fill="#5a6785">{npc_label}</text>'
            )

    svg_parts.append('</svg>')
    return f'<div class="loc-map-wrap">{"".join(svg_parts)}</div>'


def format_timeline_html(engine: GameEngine) -> str:
    return engine.get_event_timeline_html()


# =====================================================================
# App
# =====================================================================

def create_app() -> gr.Blocks:
    engine = GameEngine()
    manager = LoopManager(engine)

    with gr.Blocks(
        title="TimeLoop: The Unspeakable Midnight",
        theme=THEME,
        css=CSS,
        js=TYPEWRITER_JS,
    ) as app:

        # -- Title --
        title_md = gr.Markdown(
            f"# {t('app_title', 'en')}\n\n{t('app_subtitle', 'en')}",
            elem_classes="game-title",
        )

        # -- Info bar --
        info_bar = gr.HTML(
            value=f'<div class="info-bar"><span>{t("press_new_game", "en")}</span></div>',
        )

        # -- Main layout: [sidebar | narration center] --
        with gr.Row():

            # === Left sidebar: Map + Status ===
            with gr.Column(scale=1, min_width=220):
                with gr.Row():
                    new_game_btn = gr.Button(
                        t("btn_new_game", "en"), variant="primary",
                        elem_classes="ctrl-btn", size="sm",
                    )
                    restart_loop_btn = gr.Button(
                        t("btn_restart_loop", "en"), variant="secondary",
                        elem_classes="ctrl-btn", size="sm",
                    )
                    lang_toggle_btn = gr.Button(
                        "中", variant="secondary",
                        elem_classes="ctrl-btn lang-btn", size="sm",
                    )

                location_map = gr.HTML(value="", elem_classes="side-panel")

                status_display = gr.HTML(
                    value="",
                    elem_classes="side-panel",
                )

            # === Center: Scrolling Narration Log + Choices + Input ===
            with gr.Column(scale=3, min_width=500):
                narration_display = gr.HTML(
                    value=(
                        f'<div class="narrative-focus">'
                        f'<div class="nf-current">'
                        f'<div class="nf-scene"><div class="scene-narration">'
                        f'<p><em>{t("opening_flavor", "en")}</em></p>'
                        f'</div></div></div></div>'
                    ),
                )

                with gr.Column(elem_classes="action-area"):
                    choice_btn_1 = gr.Button("---", interactive=False, variant="secondary", elem_classes="choice-btn")
                    choice_btn_2 = gr.Button("---", interactive=False, variant="secondary", elem_classes="choice-btn")
                    choice_btn_3 = gr.Button("---", interactive=False, variant="secondary", elem_classes="choice-btn")
                    choice_btn_4 = gr.Button("---", interactive=False, variant="secondary", elem_classes="choice-btn knowledge-choice", visible=False)
                    with gr.Row():
                        player_input = gr.Textbox(
                            placeholder=t("input_placeholder", "en"),
                            label="",
                            show_label=False,
                            scale=5,
                            elem_classes="input-area",
                        )
                        submit_btn = gr.Button(
                            t("btn_act", "en"), variant="primary",
                            scale=1, elem_classes="act-btn",
                        )

        # -- Horizontal event timeline --
        with gr.Column(elem_classes="timeline-section"):
            event_timeline_display = gr.HTML(
                value=f'<div class="tl-track" style="justify-content:center;"><span style="color:#4b5563;font-size:12px;">{t("timeline_empty", "en")}</span></div>',
                elem_classes="timeline-wrap",
            )

        # -- Debug accordion --
        with gr.Accordion(t("debug_panel", "en"), open=False, visible=False, elem_classes="debug-accordion") as debug_accordion:
            with gr.Row():
                debug_intent = gr.Textbox(label=t("debug_intent", "en"), interactive=False)
                debug_sanity_delta = gr.Textbox(label=t("debug_sanity_change", "en"), interactive=False)
            debug_consistency = gr.Textbox(label=t("debug_consistency", "en"), lines=3, interactive=False)
            debug_state_json = gr.JSON(label=t("debug_state", "en"))

        debug_toggle_btn = gr.Button(
            "DBG", variant="secondary", size="sm", visible=True,
            elem_classes="debug-toggle-btn",
        )

        # -- State --
        choice_state = gr.State(value=[])
        lang_state = gr.State(value="en")
        narrative_history = gr.State(value=[])

        # -- Handlers --
        def on_new_game(lang, history):
            engine.lang = lang
            result = manager.start_new_game()
            return _update_ui(result, engine, lang, history=[], is_new_game=True)

        def on_restart_loop(lang, history):
            engine.lang = lang
            result = manager.force_restart_loop()
            return _update_ui(result, engine, lang, history=history)

        def on_submit(text, choices_data, lang, history):
            if not text.strip():
                return _no_change()
            engine.lang = lang
            result = manager.handle_input(text.strip(), choice_sanity_cost=0)
            result.player_input = text.strip()
            return _update_ui(result, engine, lang, history=history)

        def on_choice_click(idx, choices_data, lang, history):
            if not choices_data or idx >= len(choices_data):
                return _no_change()
            choice = choices_data[idx]
            text = choice.get("text", choice.get("id", "continue"))
            san_cost = int(choice.get("sanity_cost", 0))
            choice_id = choice.get("id", "")
            trust_bonus = choice.get("trust_bonus", {})
            engine.lang = lang
            result = manager.handle_input(
                text, choice_sanity_cost=san_cost, choice_id=choice_id,
                trust_bonus=trust_bonus,
            )
            result.player_input = text
            return _update_ui(result, engine, lang, history=history)

        def on_lang_toggle(current_lang):
            new_lang = "zh" if current_lang == "en" else "en"
            engine.lang = new_lang
            toggle_label = "EN" if new_lang == "zh" else "中"

            updates = [
                new_lang,
                gr.update(value=toggle_label),
                gr.update(value=f"# {t('app_title', new_lang)}\n\n{t('app_subtitle', new_lang)}"),
                gr.update(value=t("btn_new_game", new_lang)),
                gr.update(value=t("btn_restart_loop", new_lang)),
                gr.update(value=t("btn_act", new_lang)),
                gr.update(placeholder=t("input_placeholder", new_lang)),
            ]

            if engine.game_state:
                updates.append(format_info_bar(engine, new_lang))
                updates.append(format_location_map(engine, new_lang))
                updates.append(format_status(engine, new_lang))
                updates.append(format_timeline_html(engine))
            else:
                updates.append(f'<div class="info-bar"><span>{t("press_new_game", new_lang)}</span></div>')
                updates.append("")
                updates.append("")
                updates.append(f'<div class="tl-track" style="justify-content:center;"><span style="color:#4b5563;font-size:12px;">{t("timeline_empty", new_lang)}</span></div>')

            return tuple(updates)

        game_outputs = [
            info_bar,
            narration_display,
            location_map,
            status_display,
            event_timeline_display,
            choice_btn_1,
            choice_btn_2,
            choice_btn_3,
            choice_btn_4,
            player_input,
            debug_intent,
            debug_sanity_delta,
            debug_consistency,
            debug_state_json,
            choice_state,
            narrative_history,
        ]

        game_inputs_base = [lang_state, narrative_history]

        new_game_btn.click(on_new_game, inputs=game_inputs_base, outputs=game_outputs)
        restart_loop_btn.click(on_restart_loop, inputs=game_inputs_base, outputs=game_outputs)
        submit_btn.click(on_submit, inputs=[player_input, choice_state, lang_state, narrative_history], outputs=game_outputs)
        player_input.submit(on_submit, inputs=[player_input, choice_state, lang_state, narrative_history], outputs=game_outputs)

        def make_choice_handler(idx):
            def handler(choices_data, lang, history):
                return on_choice_click(idx, choices_data, lang, history)
            return handler

        for i, btn in enumerate([choice_btn_1, choice_btn_2, choice_btn_3, choice_btn_4]):
            btn.click(
                make_choice_handler(i),
                inputs=[choice_state, lang_state, narrative_history],
                outputs=game_outputs,
            )

        debug_visible = gr.State(value=False)

        def on_debug_toggle(is_visible):
            new_vis = not is_visible
            return new_vis, gr.update(visible=new_vis)

        debug_toggle_btn.click(
            on_debug_toggle,
            inputs=[debug_visible],
            outputs=[debug_visible, debug_accordion],
        )

        lang_toggle_outputs = [
            lang_state,
            lang_toggle_btn,
            title_md,
            new_game_btn,
            restart_loop_btn,
            submit_btn,
            player_input,
            info_bar,
            location_map,
            status_display,
            event_timeline_display,
        ]
        lang_toggle_btn.click(on_lang_toggle, inputs=[lang_state], outputs=lang_toggle_outputs)

    return app


# =====================================================================
# UI update helpers
# =====================================================================

def _format_choice_label(choice: dict, lang: str, idx: int = 0, is_knowledge: bool = False) -> str:
    """Plain-text label for Gradio Button (no HTML — buttons don't render it)."""
    text = choice.get("text", "...")
    cost = int(choice.get("sanity_cost", 0))

    parts = []
    if is_knowledge:
        tag = "〔前世记忆〕" if lang == "zh" else "〔PAST LIFE〕"
        parts.append(tag + " ")
    parts.append(text)
    if cost < 0:
        san_label = "理智" if lang == "zh" else "SAN"
        parts.append(f"  [{san_label} {cost}]")

    hint = choice.get("hint", "")
    if hint:
        parts.append(f"  — {hint}")

    return "".join(parts)


def _md_to_html(md: str) -> str:
    """Minimal Markdown-to-HTML for narration display."""
    import re
    html = md
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    html = re.sub(r'\n---\n', r'<hr>', html)
    paragraphs = html.split('\n\n')
    parts = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if p.startswith('<h') or p.startswith('<hr'):
            parts.append(p)
        else:
            parts.append(f'<p>{p}</p>')
    return '\n'.join(parts)


def _build_narrative_entry(result: TurnResult, lang: str, san_level: str) -> list[str]:
    """Build structured HTML entries for the focus-based narrative display."""
    entries: list[str] = []

    if result.player_input:
        entries.append(
            f'<div class="nf-player-echo">&gt; {result.player_input}</div>'
        )

    for kh in getattr(result, 'knowledge_used', []):
        if kh.get("correct_target"):
            tag = "前世记忆触发" if lang == "zh" else "MEMORY TRIGGERED"
            entries.append(f'<div class="nf-knowledge-hit"><span>[{tag}]</span></div>')
        else:
            tag = "记忆错位" if lang == "zh" else "WRONG TARGET"
            entries.append(f'<div class="nf-knowledge-fail"><span>[{tag}]</span></div>')

    scene_parts: list[str] = []

    if result.event_triggered:
        scene_parts.append(
            f'<div class="scene-event-title">{result.event_triggered}</div>'
        )

    if result.narration:
        scene_parts.append(
            f'<div class="scene-narration">{_md_to_html(result.narration)}</div>'
        )

    if result.dialogue_speaker and result.dialogue_text:
        speaker_lower = (result.dialogue_speaker or "").lower()
        npc_color = "#7eb8da"
        for npc_key, color in NPC_COLORS.items():
            if npc_key in speaker_lower:
                npc_color = color
                break
        scene_parts.append(
            f'<div class="scene-dialogue" style="--npc-color:{npc_color};">'
            f'<div class="scene-speaker">{result.dialogue_speaker}</div>'
            f'<div class="scene-text">&ldquo;{result.dialogue_text}&rdquo;</div>'
            f'</div>'
        )

    delta = result.sanity_delta
    if delta and delta != 0:
        flavor = SANITY_FLAVOR.get(san_level, SANITY_FLAVOR["lucid"])
        text = flavor.get(lang, flavor["en"])
        san_label = "理智" if lang == "zh" else "SAN"
        scene_parts.append(
            f'<div class="scene-san-flavor">{text} ({san_label} {delta:+d})</div>'
        )

    if result.is_ending:
        title = result.ending_id.replace("_", " ").title()
        scene_parts.append(
            f'<div class="scene-ending">'
            f'<div class="scene-ending-title">{title}</div>'
            f'<div class="scene-ending-text">{_md_to_html(result.ending_text or "")}</div>'
            f'</div>'
        )

    if result.event_image:
        img_url = f"/file=data/images/events/{result.event_image}"
        scene_parts.insert(0, f'<img class="scene-cg" src="{img_url}" alt="" />')

    entries.append(f'<div class="nf-scene">{"".join(scene_parts)}</div>')

    return entries


def _build_mobius_html(loop_num: int, lang: str, narration: str = "") -> str:
    """Full Möbius strip overlay HTML for loop-reset scenes."""
    title = "时间循环" if lang == "zh" else "TIME LOOP"
    sub = f"第 {loop_num} 次循环" if lang == "zh" else f"LOOP #{loop_num}"

    particles = "".join(
        f'<div class="mobius-particle p{i}"></div>' for i in range(1, 9)
    )
    narration_html = ""
    if narration:
        narration_html = f'<div class="mobius-narration">{_md_to_html(narration)}</div>'

    return (
        f'<div class="nf-scene loop-reset">'
        f'<div class="mobius-overlay">'
        f'<div class="mobius-particles">{particles}</div>'
        f'<div class="mobius-container">'
        f'<svg class="mobius-svg" viewBox="0 0 220 120">'
        f'<path d="M30,60 C30,20 80,20 110,60 C140,100 190,100 190,60 '
        f'C190,20 140,20 110,60 C80,100 30,100 30,60 Z" '
        f'fill="none" stroke="rgba(99,102,241,0.15)" stroke-width="12"/>'
        f'<path d="M30,60 C30,20 80,20 110,60 C140,100 190,100 190,60 '
        f'C190,20 140,20 110,60 C80,100 30,100 30,60 Z" '
        f'fill="none" stroke="#6366f1" stroke-width="2.5" opacity="0.6"/>'
        f'<path class="mobius-flow" '
        f'd="M30,60 C30,20 80,20 110,60 C140,100 190,100 190,60 '
        f'C190,20 140,20 110,60 C80,100 30,100 30,60 Z" '
        f'fill="none" stroke="#a78bfa" stroke-width="2" '
        f'stroke-dasharray="12 60" stroke-linecap="round"/>'
        f'</svg>'
        f'</div>'
        f'<div class="mobius-title">{title}</div>'
        f'<div class="mobius-loop-num">{sub}</div>'
        f'{narration_html}'
        f'</div>'
        f'</div>'
    )


def _update_ui(
    result: TurnResult,
    engine: GameEngine,
    lang: str = "en",
    history: list | None = None,
    is_new_game: bool = False,
):
    if history is None:
        history = []

    san_level = engine.game_state.sanity_level if engine.game_state else "lucid"

    if is_new_game:
        history = []

    if result.is_loop_reset:
        gs = engine.game_state
        loop_num = gs.loop_count if gs else 1
        divider_text = f"循环 #{loop_num}" if lang == "zh" else f"Loop #{loop_num}"
        history.append(
            f'<div class="nl-loop-divider">&#8734; {divider_text} &#8734;</div>'
        )

    if result.is_loop_reset:
        gs = engine.game_state
        loop_num = gs.loop_count if gs else 1
        new_entries = [_build_mobius_html(loop_num, lang, result.narration)]
    else:
        new_entries = _build_narrative_entry(result, lang, san_level)
    past_count = len(history)
    history.extend(new_entries)

    # --- Build two-zone HTML: collapsed history + prominent current scene ---
    past_html = ""
    if past_count > 0:
        n_scenes = sum(1 for h in history[:past_count] if 'nf-scene' in h)
        if n_scenes > 0:
            toggle_text = f"过去 {n_scenes} 幕" if lang == "zh" else f"Past {n_scenes} scenes"
            past_items = "".join(history[:past_count])
            past_html = (
                f'<div class="nf-history-toggle">'
                f'<span class="nf-toggle-icon">&#9662;</span> {toggle_text}'
                f'</div>'
                f'<div class="nf-history">{past_items}</div>'
            )

    current_html = "".join(history[past_count:])

    full_log = (
        f'<div class="narrative-focus san-{san_level}">'
        f'{past_html}'
        f'<div class="nf-current">{current_html}</div>'
        f'</div>'
    )

    info_html = format_info_bar(engine, lang)
    loc_map = format_location_map(engine, lang)
    status = format_status(engine, lang)
    timeline = format_timeline_html(engine)

    choices = list(result.choices or [])

    knowledge_choice = None
    if engine.loop_memory.total_loops > 0 and engine.game_state:
        unused = engine.loop_memory.unused_knowledge
        npcs_here = [
            npc_id for npc_id, npc in engine.game_state.characters.items()
            if npc.location == engine.game_state.location and npc.alive
        ]
        for key in unused:
            if key.target_npc in npcs_here:
                hint_text = key.hint_zh if lang == "zh" else key.hint_en
                knowledge_choice = {
                    "id": f"knowledge_{key.id}",
                    "text": hint_text,
                    "sanity_cost": 0,
                    "is_knowledge": True,
                }
                break

    btn_labels = []
    btn_interactive = []
    for i in range(3):
        if i < len(choices):
            lbl = _format_choice_label(choices[i], lang, idx=i)
            btn_labels.append(lbl)
            btn_interactive.append(True)
        else:
            btn_labels.append("---")
            btn_interactive.append(False)

    fx = SANITY_EFFECTS.get(san_level, SANITY_EFFECTS["lucid"])
    swap_chance = fx["choice_swap"]
    if swap_chance > 0 and sum(1 for b in btn_interactive if b) >= 2:
        active_idx = [i for i, b in enumerate(btn_interactive) if b]
        if san_level == "madness":
            random.shuffle(active_idx)
            shuffled = [btn_labels[i] for i in active_idx]
            for k, i in enumerate(active_idx):
                btn_labels[i] = shuffled[k]
        elif random.random() < swap_chance and len(active_idx) >= 2:
            a, b = random.sample(active_idx, 2)
            btn_labels[a], btn_labels[b] = btn_labels[b], btn_labels[a]

    has_k_choice = knowledge_choice is not None
    if has_k_choice:
        choices.append(knowledge_choice)

    k_label = _format_choice_label(knowledge_choice, lang, is_knowledge=True) if has_k_choice else "---"

    cost0 = int(choices[0].get("sanity_cost", 0)) if len(choices) > 0 else 0
    cost1 = int(choices[1].get("sanity_cost", 0)) if len(choices) > 1 else 0
    cost2 = int(choices[2].get("sanity_cost", 0)) if len(choices) > 2 else 0

    cls0 = "choice-btn" + (" high-cost" if cost0 < -10 else "")
    cls1 = "choice-btn" + (" high-cost" if cost1 < -10 else "")
    cls2 = "choice-btn" + (" high-cost" if cost2 < -10 else "")

    state_data = engine.get_state_summary()

    return (
        info_html,
        full_log,
        loc_map,
        status,
        timeline,
        gr.update(value=btn_labels[0], interactive=btn_interactive[0], elem_classes=cls0),
        gr.update(value=btn_labels[1], interactive=btn_interactive[1], elem_classes=cls1),
        gr.update(value=btn_labels[2], interactive=btn_interactive[2], elem_classes=cls2),
        gr.update(value=k_label, interactive=has_k_choice, visible=has_k_choice, elem_classes="choice-btn knowledge-choice"),
        gr.update(value=""),
        result.intent,
        f"{result.sanity_delta:+d}" if result.sanity_delta else "0",
        result.consistency_log or "(clean)",
        state_data,
        choices,
        history,
    )


def _no_change():
    return tuple(gr.update() for _ in range(16))


if __name__ == "__main__":
    app = create_app()
    app.launch(share=False, allowed_paths=["data/images/events"])
