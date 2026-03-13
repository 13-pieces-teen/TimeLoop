from __future__ import annotations

import gradio as gr

from src.game.engine import GameEngine, TurnResult
from src.game.loop_manager import LoopManager
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

CSS = """
/* -- Header -- */
.header-row { margin-bottom: 4px !important; }
.game-title {
    text-align: center;
    padding: 8px 0 2px 0;
}
.game-title h1 {
    font-size: 1.8em !important;
    color: #ccd6f6 !important;
    letter-spacing: 2px;
    margin-bottom: 0 !important;
}
.game-title p {
    color: #5a6785 !important;
    font-style: italic;
    font-size: 0.95em;
    margin-top: 2px !important;
}

/* -- Top info bar -- */
.info-bar {
    display: flex;
    align-items: center;
    gap: 24px;
    padding: 8px 16px;
    background: linear-gradient(90deg, #0f1628 0%, #131829 50%, #0f1628 100%);
    border: 1px solid #1e2a4a;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85em;
    color: #8892b0;
    margin-bottom: 4px;
}
.info-bar .sanity-section { flex: 1; }
.info-bar .meta-section { text-align: right; }

/* -- Narration area -- */
.narration-panel {
    padding: 24px 28px !important;
    border-left: 3px solid #1a3a5c !important;
    background: linear-gradient(135deg, #0d1117 0%, #131829 100%) !important;
    min-height: 180px !important;
    font-size: 1.1em !important;
    line-height: 1.9 !important;
    color: #c9d1d9 !important;
    border-radius: 8px !important;
}
.narration-panel p { margin-bottom: 12px !important; }
.narration-panel strong { color: #7eb8da !important; }
.narration-panel em { color: #a8b2d1 !important; }

/* -- Action area (vertical choices + input) -- */
.action-area {
    gap: 6px !important;
    margin-top: 8px !important;
}

/* -- Choice buttons (vertical cards) -- */
.choice-btn {
    min-height: 44px !important;
    font-size: 0.95em !important;
    border: 1px solid #1e2a4a !important;
    transition: all 0.2s ease !important;
    white-space: normal !important;
    line-height: 1.4 !important;
    padding: 10px 20px !important;
    text-align: left !important;
    width: 100% !important;
    justify-content: flex-start !important;
    border-radius: 6px !important;
}
.choice-btn:hover {
    border-color: #3d5a80 !important;
    background: #1a2744 !important;
    color: #ccd6f6 !important;
}

/* -- Input area -- */
.input-area textarea {
    background: #0d1117 !important;
    border-color: #1e2a4a !important;
    color: #c9d1d9 !important;
    font-size: 1em !important;
}
.act-btn {
    min-height: 42px !important;
    font-weight: 600 !important;
    letter-spacing: 1px !important;
}

/* -- Side panels -- */
.side-panel textarea {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.8em !important;
    line-height: 1.6 !important;
    color: #8892b0 !important;
    background: #0d1117 !important;
    border-color: #1e2a4a !important;
}

/* -- Status panel (HTML) -- */
.status-html {
    font-family: 'Crimson Text', serif;
    font-size: 0.9em;
    color: #8892b0;
    max-height: 520px;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: #1e2a4a #0d1117;
}
.sp-section {
    background: #0d1117;
    border: 1px solid #1e2a4a;
    border-radius: 6px;
    padding: 10px 12px;
    margin-bottom: 8px;
}
.sp-header {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7em;
    font-weight: 700;
    letter-spacing: 2px;
    color: #5a6785;
    text-transform: uppercase;
    margin-bottom: 8px;
}
/* items */
.sp-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    color: #a8b2d1;
    font-size: 0.88em;
}
.sp-item-icon {
    font-size: 1.1em;
    width: 20px;
    text-align: center;
    flex-shrink: 0;
}
.sp-item-name { flex: 1; }
/* npc rows */
.sp-npc { margin-bottom: 8px; }
.sp-npc-row {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 2px;
}
.sp-npc-name {
    flex: 1;
    color: #ccd6f6;
    font-size: 0.88em;
    font-weight: 600;
}
.sp-dots { display: flex; gap: 3px; }
.sp-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #1f2937;
    border: 1px solid #374151;
}
.sp-dot.filled-gray { background: #6b7280; border-color: #6b7280; }
.sp-dot.filled-blue { background: #3b82f6; border-color: #3b82f6; box-shadow: 0 0 4px #3b82f633; }
.sp-dot.filled-green { background: #22c55e; border-color: #22c55e; box-shadow: 0 0 4px #22c55e33; }
.sp-dot.filled-gold { background: #eab308; border-color: #eab308; box-shadow: 0 0 4px #eab30833; }
.sp-trust-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75em;
    color: #5a6785;
    min-width: 20px;
    text-align: right;
}
.sp-npc-hint {
    font-size: 0.78em;
    color: #5a6785;
    font-style: italic;
    padding-left: 4px;
}
.sp-npc-loc {
    font-size: 0.75em;
    color: #4b5563;
    padding-left: 4px;
}
/* facts */
.sp-cat-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68em;
    color: #3b82f6;
    letter-spacing: 1px;
    margin-top: 6px;
    margin-bottom: 4px;
}
.sp-fact {
    padding: 2px 0 2px 8px;
    font-size: 0.82em;
    color: #8892b0;
    border-left: 2px solid #1e2a4a;
    margin-bottom: 3px;
    line-height: 1.4;
}
.sp-empty {
    color: #4b5563;
    font-style: italic;
    font-size: 0.85em;
}

/* -- Game control buttons -- */
.ctrl-btn {
    font-size: 0.85em !important;
    padding: 6px 12px !important;
}

/* -- Language toggle -- */
.lang-btn {
    min-width: 44px !important;
    max-width: 44px !important;
    font-size: 0.8em !important;
    padding: 4px 8px !important;
    font-weight: 700 !important;
    letter-spacing: 1px !important;
}

/* -- Horizontal timeline -- */
.timeline-section {
    margin-top: 8px !important;
    padding: 0 !important;
}
.timeline-wrap {
    background: linear-gradient(180deg, #0a0d16 0%, #0d1117 100%) !important;
    border: 1px solid #1e2a4a !important;
    border-radius: 8px !important;
    padding: 0 !important;
    overflow: hidden !important;
}
.tl-track {
    display: flex;
    align-items: flex-start;
    gap: 0;
    padding: 16px 20px 18px 20px;
    overflow-x: auto;
    scrollbar-width: thin;
    scrollbar-color: #1e2a4a #0d1117;
}
.tl-track::-webkit-scrollbar { height: 5px; }
.tl-track::-webkit-scrollbar-track { background: #0d1117; }
.tl-track::-webkit-scrollbar-thumb { background: #1e2a4a; border-radius: 4px; }

.tl-act-group {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex-shrink: 0;
}
.tl-act-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    padding: 2px 10px;
    border-radius: 10px;
    margin-bottom: 10px;
    white-space: nowrap;
}
.tl-act-done { color: #6ee7b7; background: #0d2818; border: 1px solid #16a34a44; }
.tl-act-current { color: #93c5fd; background: #0c1a3a; border: 1px solid #3b82f644; }
.tl-act-locked { color: #4b5563; background: #111318; border: 1px solid #1f293744; }

.tl-events {
    display: flex;
    align-items: flex-start;
    gap: 0;
}

/* --- Nodes --- */
.tl-node {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 110px;
    flex-shrink: 0;
}
.tl-dot {
    width: 18px; height: 18px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-bottom: 8px;
    transition: all 0.3s;
}
.tl-dot-done {
    background: #2dd4bf;
    box-shadow: 0 0 8px #2dd4bf55;
}
.tl-dot-active {
    background: #3b82f6;
    box-shadow: 0 0 10px #3b82f688, 0 0 20px #3b82f633;
    animation: tl-pulse 2s ease-in-out infinite;
}
.tl-dot-pending {
    background: #1f2937;
    border: 2px solid #374151;
}
.tl-dot-locked {
    background: #111827;
    border: 2px solid #1f2937;
}

@keyframes tl-pulse {
    0%, 100% { box-shadow: 0 0 10px #3b82f688, 0 0 20px #3b82f633; }
    50% { box-shadow: 0 0 14px #3b82f6aa, 0 0 28px #3b82f655; }
}

/* --- Cards --- */
.tl-card {
    width: 100px;
    padding: 6px 8px;
    border-radius: 6px;
    text-align: center;
    transition: all 0.2s;
}
.tl-card-done {
    background: #0d2818;
    border: 1px solid #16a34a55;
}
.tl-card-done .tl-title { color: #a7f3d0; }
.tl-card-done .tl-sub { color: #6ee7b7; }

.tl-card-active {
    background: #0c1a3a;
    border: 1px solid #3b82f666;
    box-shadow: 0 2px 12px #3b82f622;
}
.tl-card-active .tl-title { color: #bfdbfe; }
.tl-card-active .tl-sub { color: #93c5fd; }

.tl-card-pending {
    background: #111827;
    border: 1px solid #1f2937;
}
.tl-card-pending .tl-title { color: #6b7280; }
.tl-card-pending .tl-sub { color: #4b5563; }

.tl-card-locked {
    background: #0d0f14;
    border: 1px solid #1a1d27;
    min-height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.tl-title {
    font-size: 11px;
    font-weight: 600;
    line-height: 1.3;
    margin-bottom: 2px;
}
.tl-sub {
    font-size: 9px;
    opacity: 0.7;
    line-height: 1.2;
}
.tl-lock {
    font-size: 14px;
    opacity: 0.3;
    filter: grayscale(1);
}

/* --- Connector lines --- */
.tl-line {
    width: 24px;
    height: 2px;
    margin-top: 8px;
    flex-shrink: 0;
    align-self: flex-start;
    border-radius: 1px;
}
.tl-line-done { background: linear-gradient(90deg, #2dd4bf, #2dd4bf88); }
.tl-line-dim { background: #1f2937; }

.tl-bridge {
    width: 32px;
    height: 2px;
    margin-top: 34px;
    flex-shrink: 0;
    border-radius: 1px;
}
.tl-bridge-done { background: linear-gradient(90deg, #16a34a66, #16a34a22); }
.tl-bridge-dim { background: #1a1d2744; }

/* -- Accordion -- */
.debug-accordion {
    border-color: #1e2a4a !important;
    margin-top: 8px !important;
}

/* -- Debug toggle (tiny corner button) -- */
.debug-toggle-btn {
    position: fixed !important;
    bottom: 8px !important;
    right: 8px !important;
    width: 40px !important;
    min-width: 40px !important;
    height: 24px !important;
    font-size: 9px !important;
    opacity: 0.25 !important;
    z-index: 999 !important;
    padding: 0 !important;
}
.debug-toggle-btn:hover { opacity: 0.8 !important; }

/* ============================================================
   SANITY VISUAL EFFECTS -- 4-level progressive UI corruption
   ============================================================ */

/* --- Keyframes --- */
@keyframes san-breathe {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.82; }
}
@keyframes san-breathe-fast {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}
@keyframes san-breathe-violent {
    0%, 100% { opacity: 1; }
    30% { opacity: 0.5; }
    60% { opacity: 0.9; }
    80% { opacity: 0.4; }
}
@keyframes san-hue-drift {
    0%, 100% { filter: hue-rotate(0deg); }
    50% { filter: hue-rotate(8deg); }
}
@keyframes san-hue-violent {
    0%, 100% { filter: hue-rotate(0deg) saturate(1.1); }
    33% { filter: hue-rotate(12deg) saturate(1.3); }
    66% { filter: hue-rotate(-5deg) saturate(0.9); }
}
@keyframes san-skew-subtle {
    0%, 100% { transform: skewX(0deg); }
    25% { transform: skewX(-0.3deg); }
    75% { transform: skewX(0.3deg); }
}
@keyframes san-skew-violent {
    0%, 100% { transform: skewX(0deg) skewY(0deg) scale(1); }
    15% { transform: skewX(-0.6deg) skewY(0.2deg) scale(1.002); }
    40% { transform: skewX(0.8deg) skewY(-0.3deg) scale(0.998); }
    65% { transform: skewX(-0.4deg) skewY(0.4deg) scale(1.003); }
    85% { transform: skewX(0.5deg) skewY(-0.1deg) scale(0.997); }
}
@keyframes san-border-pulse {
    0%, 100% { border-left-width: 3px; }
    50% { border-left-width: 6px; }
}
@keyframes san-text-shadow-flicker {
    0%, 100% { text-shadow: none; }
    20% { text-shadow: 2px 0 #8b250066; }
    40% { text-shadow: -1px 0 #cc000044; }
    60% { text-shadow: 1px 1px #8b250055; }
    80% { text-shadow: none; }
}
@keyframes san-text-shadow-violent {
    0%, 100% { text-shadow: none; }
    10% { text-shadow: 3px 0 #cc0000aa, -2px 0 #7700cc55; }
    25% { text-shadow: -2px 1px #cc000088; }
    40% { text-shadow: 1px -1px #7700cc66, 2px 2px #cc000044; }
    55% { text-shadow: none; }
    70% { text-shadow: -3px 0 #cc0000bb, 1px 1px #7700cc77; }
    85% { text-shadow: 2px -1px #cc000066; }
}
@keyframes san-flicker {
    0%, 95%, 100% { opacity: 1; }
    96% { opacity: 0.3; }
    97% { opacity: 0.8; }
    98% { opacity: 0.1; }
    99% { opacity: 0.7; }
}
@keyframes san-border-color-flicker {
    0%, 100% { border-color: #1e2a4a; }
    30% { border-color: #8b2500; }
    60% { border-color: #1e2a4a; }
    80% { border-color: #cc0000; }
}
@keyframes san-time-jitter {
    0%, 100% { transform: translateX(0); }
    20% { transform: translateX(1px); }
    40% { transform: translateX(-2px); }
    60% { transform: translateX(1px); }
    80% { transform: translateX(-1px); }
}

/* --- UNEASY (50-79) --- */
.info-bar.san-uneasy .san-value {
    animation: san-breathe 3s ease-in-out infinite;
}
.narration-panel.san-uneasy {
    border-left-color: #92711a !important;
    background: linear-gradient(135deg, #0d1117 0%, #1a1708 100%) !important;
}

/* --- DISTORTED (20-49) --- */
.info-bar.san-distorted .san-value {
    animation: san-breathe-fast 1.5s ease-in-out infinite;
}
.narration-panel.san-distorted {
    border-left-color: #8b2500 !important;
    background: linear-gradient(135deg, #0d1117 0%, #170808 100%) !important;
    animation: san-skew-subtle 4s ease-in-out infinite, san-hue-drift 6s ease-in-out infinite;
}
.narration-panel.san-distorted p {
    animation: san-text-shadow-flicker 5s linear infinite;
}

/* --- MADNESS (0-19) --- */
.info-bar.san-madness .san-value {
    animation: san-breathe-violent 0.5s ease-in-out infinite;
    filter: blur(0.5px);
}
.info-bar.san-madness .meta-time {
    animation: san-time-jitter 1.5s linear infinite;
    display: inline-block;
}
.narration-panel.san-madness {
    border-left-color: #cc0000 !important;
    background: linear-gradient(135deg, #1a0505 0%, #170808 60%, #0d0508 100%) !important;
    animation:
        san-skew-violent 3s ease-in-out infinite,
        san-border-pulse 2s ease-in-out infinite,
        san-hue-violent 2s linear infinite;
}
.narration-panel.san-madness p {
    animation: san-text-shadow-violent 3s linear infinite, san-flicker 8s step-end infinite;
}
"""


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


def format_info_bar(engine: GameEngine, lang: str = "en") -> str:
    if not engine.game_state:
        return f'<div class="info-bar san-lucid"><span>{t("press_new_game", lang)}</span></div>'
    gs = engine.game_state
    lm = engine.loop_memory

    sanity = gs.sanity
    level = gs.sanity_level
    color = SANITY_COLORS.get(level, "#fff")
    filled = int(sanity / 5)
    bar = "\u2588" * filled + "\u2591" * (20 - filled)
    level_label = t(f"san_{level}", lang)

    loop_info = f"{t('loop_label', lang)} #{gs.loop_count}"
    if lm.total_loops > 0:
        loop_info += f" ({t('memories_label', lang)}: {lm.total_loops})"

    location = loc_name(gs.location, lang)

    return (
        f'<div class="info-bar san-{level}">'
        f'<div class="sanity-section">'
        f'<span class="san-value" style="color:{color}; font-weight:600;">{bar} {sanity}/100 [{level_label}]</span>'
        f'</div>'
        f'<div class="meta-section">'
        f'<span class="meta-time">{gs.current_time_str} ({gs.minutes_until_midnight} {t("min_left", lang)})</span> '
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

    # --- NPCs ---
    npc_label = t("label_npcs", lang)
    here_label = "此地" if lang == "zh" else "Here"
    html_parts.append(f'<div class="sp-section"><div class="sp-header">{npc_label}</div>')

    here_npcs = []
    away_npcs = []
    for npc_id, npc in gs.characters.items():
        if npc.location == gs.location and npc.alive:
            here_npcs.append((npc_id, npc))
        elif npc.alive:
            away_npcs.append((npc_id, npc))

    for npc_id, npc in here_npcs:
        hint = _get_trust_hint(npc.trust, lang)
        dots = _trust_dots_html(npc.trust)
        html_parts.append(f'<div class="sp-npc">')
        html_parts.append(
            f'<div class="sp-npc-row">'
            f'<span class="sp-npc-name">{npc.name}</span>'
            f'<div class="sp-dots">{dots}</div>'
            f'<span class="sp-trust-num">{npc.trust}</span>'
            f'</div>'
        )
        if hint:
            html_parts.append(f'<div class="sp-npc-hint">{hint}</div>')
        html_parts.append('</div>')

    if away_npcs:
        for npc_id, npc in away_npcs:
            loc_label = loc_name(npc.location, lang)
            dots = _trust_dots_html(npc.trust)
            html_parts.append(f'<div class="sp-npc">')
            html_parts.append(
                f'<div class="sp-npc-row">'
                f'<span class="sp-npc-name" style="color:#6b7280;">{npc.name}</span>'
                f'<div class="sp-dots">{dots}</div>'
                f'<span class="sp-trust-num">{npc.trust}</span>'
                f'</div>'
            )
            html_parts.append(f'<div class="sp-npc-loc">@ {loc_label}</div>')
            html_parts.append('</div>')

    if not here_npcs and not away_npcs:
        no_one = "无人" if lang == "zh" else "(no one)"
        html_parts.append(f'<div class="sp-empty">{no_one}</div>')
    html_parts.append('</div>')

    # --- Facts ---
    facts_label = t("label_facts", lang)
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
                html_parts.append(f'<div class="sp-fact">{text}</div>')
    else:
        empty = "尚无线索" if lang == "zh" else "No clues yet"
        html_parts.append(f'<div class="sp-empty">{empty}</div>')
    html_parts.append('</div>')

    html_parts.append('</div>')
    return "".join(html_parts)


def format_timeline_html(engine: GameEngine) -> str:
    return engine.get_event_timeline_html()


# =====================================================================
# App
# =====================================================================

def create_app() -> gr.Blocks:
    engine = GameEngine()
    manager = LoopManager(engine)

    with gr.Blocks(title="TimeLoop: The Unspeakable Midnight", theme=THEME, css=CSS) as app:

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

            # === Left sidebar: Status ===
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

                status_display = gr.HTML(
                    value="",
                    elem_classes="side-panel",
                )

            # === Center: Narration + Choices + Input ===
            with gr.Column(scale=3, min_width=500):
                narration_display = gr.HTML(
                    value=f'<div class="narration-panel san-lucid"><p><em>{t("opening_flavor", "en")}</em></p></div>',
                )

                with gr.Column(elem_classes="action-area"):
                    choice_btn_1 = gr.Button("---", interactive=False, variant="secondary", elem_classes="choice-btn")
                    choice_btn_2 = gr.Button("---", interactive=False, variant="secondary", elem_classes="choice-btn")
                    choice_btn_3 = gr.Button("---", interactive=False, variant="secondary", elem_classes="choice-btn")
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

        # -- Debug accordion (hidden by default, triple-click title to reveal) --
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

        # -- Handlers --
        def on_new_game(lang):
            engine.lang = lang
            result = manager.start_new_game()
            return _update_ui(result, engine, lang)

        def on_restart_loop(lang):
            engine.lang = lang
            result = manager.force_restart_loop()
            return _update_ui(result, engine, lang)

        def on_submit(text, choices_data, lang):
            if not text.strip():
                return _no_change()
            engine.lang = lang
            result = manager.handle_input(text.strip(), choice_sanity_cost=0)
            return _update_ui(result, engine, lang)

        def on_choice_click(idx, choices_data, lang):
            if not choices_data or idx >= len(choices_data):
                return _no_change()
            choice = choices_data[idx]
            text = choice.get("text", choice.get("id", "continue"))
            san_cost = int(choice.get("sanity_cost", 0))
            choice_id = choice.get("id", "")
            engine.lang = lang
            result = manager.handle_input(text, choice_sanity_cost=san_cost, choice_id=choice_id)
            return _update_ui(result, engine, lang)

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
                updates.append(format_status(engine, new_lang))
                updates.append(format_timeline_html(engine))
            else:
                updates.append(f'<div class="info-bar"><span>{t("press_new_game", new_lang)}</span></div>')
                updates.append("")
                updates.append(f'<div class="tl-track" style="justify-content:center;"><span style="color:#4b5563;font-size:12px;">{t("timeline_empty", new_lang)}</span></div>')

            return tuple(updates)

        game_outputs = [
            info_bar,
            narration_display,
            status_display,
            event_timeline_display,
            choice_btn_1,
            choice_btn_2,
            choice_btn_3,
            player_input,
            debug_intent,
            debug_sanity_delta,
            debug_consistency,
            debug_state_json,
            choice_state,
        ]

        new_game_btn.click(on_new_game, inputs=[lang_state], outputs=game_outputs)
        restart_loop_btn.click(on_restart_loop, inputs=[lang_state], outputs=game_outputs)
        submit_btn.click(on_submit, inputs=[player_input, choice_state, lang_state], outputs=game_outputs)
        player_input.submit(on_submit, inputs=[player_input, choice_state, lang_state], outputs=game_outputs)

        def make_choice_handler(idx):
            def handler(choices_data, lang):
                return on_choice_click(idx, choices_data, lang)
            return handler

        for i, btn in enumerate([choice_btn_1, choice_btn_2, choice_btn_3]):
            btn.click(
                make_choice_handler(i),
                inputs=[choice_state, lang_state],
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
            status_display,
            event_timeline_display,
        ]
        lang_toggle_btn.click(on_lang_toggle, inputs=[lang_state], outputs=lang_toggle_outputs)

    return app


# =====================================================================
# UI update helpers
# =====================================================================

def _format_choice_label(choice: dict, lang: str) -> str:
    text = choice.get("text", "...")
    cost = int(choice.get("sanity_cost", 0))
    if cost < 0:
        tag = f"[{'理智' if lang == 'zh' else 'SAN'} {cost}]"
        return f"{text}  {tag}"
    return text


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


def _update_ui(result: TurnResult, engine: GameEngine, lang: str = "en"):
    san_level = engine.game_state.sanity_level if engine.game_state else "lucid"
    narration_md = format_narration(result, lang, sanity_level=san_level)
    if result.is_ending:
        icon = "---" if result.ending_id in ("sinking_into_the_deep", "sanity_break") else "***"
        title = result.ending_id.replace("_", " ").title()
        narration_md += f"\n\n{icon}\n\n## {title}\n\n{result.ending_text}"

    narration_html = f'<div class="narration-panel san-{san_level}">{_md_to_html(narration_md)}</div>'

    info_html = format_info_bar(engine, lang)
    status = format_status(engine, lang)
    timeline = format_timeline_html(engine)

    choices = result.choices or []
    btn_labels = [_format_choice_label(choices[i], lang) if i < len(choices) else "---" for i in range(3)]
    btn_interactive = [i < len(choices) for i in range(3)]

    state_data = engine.get_state_summary()

    return (
        info_html,
        narration_html,
        status,
        timeline,
        gr.update(value=btn_labels[0], interactive=btn_interactive[0]),
        gr.update(value=btn_labels[1], interactive=btn_interactive[1]),
        gr.update(value=btn_labels[2], interactive=btn_interactive[2]),
        gr.update(value=""),
        result.intent,
        f"{result.sanity_delta:+d}" if result.sanity_delta else "0",
        result.consistency_log or "(clean)",
        state_data,
        choices,
    )


def _no_change():
    return tuple(gr.update() for _ in range(13))


if __name__ == "__main__":
    app = create_app()
    app.launch(share=False)
