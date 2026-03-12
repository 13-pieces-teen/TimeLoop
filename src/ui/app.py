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

/* -- Choice buttons -- */
.choice-btn {
    min-height: 52px !important;
    font-size: 0.95em !important;
    border: 1px solid #1e2a4a !important;
    transition: all 0.2s ease !important;
    white-space: normal !important;
    line-height: 1.4 !important;
    padding: 10px 16px !important;
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
"""


# =====================================================================
# Formatters (all accept lang)
# =====================================================================

def format_narration(result: TurnResult, lang: str = "en") -> str:
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
    return "".join(parts)


def format_info_bar(engine: GameEngine, lang: str = "en") -> str:
    if not engine.game_state:
        return f'<div class="info-bar"><span>{t("press_new_game", lang)}</span></div>'
    gs = engine.game_state
    lm = engine.loop_memory

    sanity = gs.sanity
    level = gs.sanity_level
    color = SANITY_COLORS.get(level, "#fff")
    filled = int(sanity / 5)
    bar = "\u2588" * filled + "\u2591" * (20 - filled)

    loop_info = f"{t('loop_label', lang)} #{gs.loop_count}"
    if lm.total_loops > 0:
        loop_info += f" ({t('memories_label', lang)}: {lm.total_loops})"

    location = loc_name(gs.location, lang)

    return (
        f'<div class="info-bar">'
        f'<div class="sanity-section">'
        f'<span style="color:{color}; font-weight:600;">{bar} {sanity}/100 [{level.upper()}]</span>'
        f'</div>'
        f'<div class="meta-section">'
        f'{gs.current_time_str} ({gs.minutes_until_midnight} {t("min_left", lang)}) '
        f'&nbsp;|&nbsp; {loop_info} &nbsp;|&nbsp; {t("turn_label", lang)} {gs.turn} '
        f'&nbsp;|&nbsp; {location}'
        f'</div>'
        f'</div>'
    )


TRUST_THRESHOLDS = [30, 40, 50, 60, 70, 90]

TRUST_HINTS_ZH = {
    "close": "似乎快要对你说什么了",
    "warming": "正在慢慢信任你",
    "guarded": "对你还很警惕",
}
TRUST_HINTS_EN = {
    "close": "seems about to tell you something",
    "warming": "is warming up to you",
    "guarded": "is still guarded around you",
}


def _get_trust_hint(trust: int, lang: str) -> str:
    hints = TRUST_HINTS_ZH if lang == "zh" else TRUST_HINTS_EN
    next_threshold = next((t for t in TRUST_THRESHOLDS if t > trust), None)
    if next_threshold is None:
        return ""
    gap = next_threshold - trust
    if gap <= 10:
        return f" -- {hints['close']}"
    if gap <= 25:
        return f" -- {hints['warming']}"
    return ""


def format_status(engine: GameEngine, lang: str = "en") -> str:
    if not engine.game_state:
        return ""
    gs = engine.game_state

    inv_label = t("label_inventory", lang)
    inv_items = ", ".join(gs.inventory) or t("inventory_empty", lang)
    lines = [f"{inv_label}: {inv_items}", ""]

    lines.append(f"{t('label_npcs', lang)}:")
    for npc_id, npc in gs.characters.items():
        here = " *" if npc.location == gs.location else ""
        bar_len = npc.trust // 10
        trust_bar = "=" * bar_len + "-" * (10 - bar_len)
        hint = _get_trust_hint(npc.trust, lang)
        lines.append(f"  {npc.name}{here}")
        lines.append(f"    [{trust_bar}] {npc.trust}{hint}")

    if gs.discovered_facts:
        lines.append("")
        lines.append(f"{t('label_facts', lang)}: {len(gs.discovered_facts)}")
        for f in gs.discovered_facts[-5:]:
            lines.append(f"  - {f.replace('_', ' ')}")
        if len(gs.discovered_facts) > 5:
            lines.append(f"  ... {t('facts_more', lang, n=str(len(gs.discovered_facts) - 5))}")

    return "\n".join(lines)


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

                status_display = gr.Textbox(
                    value="",
                    label=t("label_status", "en"),
                    lines=16,
                    max_lines=20,
                    interactive=False,
                    elem_classes="side-panel",
                )

            # === Center: Narration + Choices + Input ===
            with gr.Column(scale=3, min_width=500):
                narration_display = gr.Markdown(
                    value=t("opening_flavor", "en"),
                    elem_classes="narration-panel",
                )

                with gr.Row(equal_height=True):
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

        # -- Debug accordion --
        with gr.Accordion(t("debug_panel", "en"), open=False, elem_classes="debug-accordion"):
            with gr.Row():
                debug_intent = gr.Textbox(label=t("debug_intent", "en"), interactive=False)
                debug_sanity_delta = gr.Textbox(label=t("debug_sanity_change", "en"), interactive=False)
            debug_consistency = gr.Textbox(label=t("debug_consistency", "en"), lines=3, interactive=False)
            debug_state_json = gr.JSON(label=t("debug_state", "en"))

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
            result = manager.handle_input(text.strip())
            return _update_ui(result, engine, lang)

        def on_choice_click(idx, choices_data, lang):
            if not choices_data or idx >= len(choices_data):
                return _no_change()
            choice = choices_data[idx]
            text = choice.get("text", choice.get("id", "continue"))
            engine.lang = lang
            result = manager.handle_input(text)
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

def _update_ui(result: TurnResult, engine: GameEngine, lang: str = "en"):
    narration = format_narration(result, lang)
    if result.is_ending:
        icon = "---" if result.ending_id in ("sinking_into_the_deep", "sanity_break") else "***"
        title = result.ending_id.replace("_", " ").title()
        narration += f"\n\n{icon}\n\n## {title}\n\n{result.ending_text}"

    info_html = format_info_bar(engine, lang)
    status = format_status(engine, lang)
    timeline = format_timeline_html(engine)

    choices = result.choices or []
    btn_labels = [choices[i]["text"] if i < len(choices) else "---" for i in range(3)]
    btn_interactive = [i < len(choices) for i in range(3)]

    state_data = engine.get_state_summary()

    return (
        info_html,
        narration,
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
