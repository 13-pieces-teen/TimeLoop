from __future__ import annotations

import json

import gradio as gr

from src.game.engine import GameEngine, TurnResult
from src.game.loop_manager import LoopManager

SANITY_COLORS = {
    "lucid": "#4ade80",
    "uneasy": "#facc15",
    "distorted": "#f97316",
    "madness": "#ef4444",
}


def format_narration(result: TurnResult) -> str:
    parts = []
    if result.event_triggered:
        parts.append(f"**[ {result.event_triggered} ]**\n")
    parts.append(result.narration or "")
    if result.dialogue_speaker and result.dialogue_text:
        parts.append(f'\n\n**{result.dialogue_speaker}:** *"{result.dialogue_text}"*')
    return "".join(parts)


def format_status(engine: GameEngine) -> str:
    if not engine.game_state:
        return "No active game"

    gs = engine.game_state
    lm = engine.loop_memory

    npc_info = []
    for npc_id, npc in gs.characters.items():
        marker = " 📍" if npc.location == gs.location else ""
        bar_len = npc.trust // 10
        trust_bar = "█" * bar_len + "░" * (10 - bar_len)
        npc_info.append(f"  {npc.name}{marker}\n    [{trust_bar}] {npc.trust}/100")

    lines = [
        f"⏰ {gs.current_time_str}  ({gs.minutes_until_midnight} min to midnight)",
        f"🔄 Loop #{gs.loop_count}  |  Turn {gs.turn}",
        f"📍 {gs.location.replace('_', ' ').title()}",
        f"🧠 Sanity: {gs.sanity}/100 ({gs.sanity_level})",
        f"🎒 {', '.join(gs.inventory) or '(empty)'}",
        "",
        "NPCs:",
        *npc_info,
    ]

    if gs.discovered_facts:
        lines.append("")
        lines.append(f"📜 Facts: {len(gs.discovered_facts)} discovered")

    if lm.total_loops > 0:
        lines.append("")
        lines.append(f"🔮 Memories from {lm.total_loops} past loop(s)")

    return "\n".join(lines)


def format_sanity_bar(engine: GameEngine) -> str:
    if not engine.game_state:
        return ""
    sanity = engine.game_state.sanity
    level = engine.game_state.sanity_level
    color = SANITY_COLORS.get(level, "#ffffff")
    filled = int(sanity / 5)
    bar = "█" * filled + "░" * (20 - filled)
    return f'<span style="color:{color}; font-family: monospace; font-size: 1.1em;">{bar} {sanity}/100 [{level.upper()}]</span>'


def create_app() -> gr.Blocks:
    engine = GameEngine()
    manager = LoopManager(engine)

    with gr.Blocks(title="TimeLoop: The Unspeakable Midnight") as app:
        gr.Markdown(
            "# 🌙 TimeLoop: The Unspeakable Midnight\n"
            "*A Lovecraftian time-loop text adventure powered by AI*",
        )

        with gr.Row():
            # === Left: Main game area ===
            with gr.Column(scale=3):
                sanity_display = gr.HTML(value="", label="Sanity")
                narration_display = gr.Markdown(
                    value="*Press 'New Game' to begin your investigation...*",
                )

                with gr.Row():
                    choice_btn_1 = gr.Button("---", interactive=False, variant="secondary")
                    choice_btn_2 = gr.Button("---", interactive=False, variant="secondary")
                    choice_btn_3 = gr.Button("---", interactive=False, variant="secondary")

                with gr.Row():
                    player_input = gr.Textbox(
                        placeholder="Type your action (or click a choice above)...",
                        label="Your Action",
                        scale=4,
                    )
                    submit_btn = gr.Button("Act", variant="primary", scale=1)

            # === Right: Status + Event timeline ===
            with gr.Column(scale=1):
                new_game_btn = gr.Button("🌑 New Game", variant="primary")
                restart_loop_btn = gr.Button("🔄 Restart Loop", variant="secondary")

                status_display = gr.Textbox(
                    value="No active game",
                    label="Status",
                    lines=12,
                    interactive=False,
                )

                event_timeline_display = gr.Textbox(
                    value="",
                    label="Event Timeline",
                    lines=10,
                    interactive=False,
                )

        with gr.Accordion("🔍 Debug Panel", open=False):
            with gr.Row():
                debug_intent = gr.Textbox(label="Detected Intent", interactive=False)
                debug_sanity_delta = gr.Textbox(label="Sanity Change", interactive=False)
            debug_consistency = gr.Textbox(
                label="Consistency Log", lines=4, interactive=False
            )
            debug_state_json = gr.JSON(label="Full State")

        choice_state = gr.State(value=[])

        def on_new_game():
            result = manager.start_new_game()
            return _update_ui(result, engine, [])

        def on_restart_loop():
            result = manager.force_restart_loop()
            return _update_ui(result, engine, [])

        def on_submit(text, choices_data):
            if not text.strip():
                return _no_change(engine, choices_data)
            result = manager.handle_input(text.strip())
            return _update_ui(result, engine, choices_data)

        def on_choice_click(idx, choices_data):
            if not choices_data or idx >= len(choices_data):
                return _no_change(engine, choices_data)
            choice = choices_data[idx]
            text = choice.get("text", choice.get("id", "continue"))
            result = manager.handle_input(text)
            return _update_ui(result, engine, choices_data)

        outputs = [
            narration_display,
            sanity_display,
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

        new_game_btn.click(on_new_game, outputs=outputs)
        restart_loop_btn.click(on_restart_loop, outputs=outputs)
        submit_btn.click(on_submit, inputs=[player_input, choice_state], outputs=outputs)
        player_input.submit(on_submit, inputs=[player_input, choice_state], outputs=outputs)

        def make_choice_handler(idx):
            def handler(choices_data):
                return on_choice_click(idx, choices_data)
            return handler

        for i, btn in enumerate([choice_btn_1, choice_btn_2, choice_btn_3]):
            btn.click(
                make_choice_handler(i),
                inputs=[choice_state],
                outputs=outputs,
            )

    return app


def _update_ui(result: TurnResult, engine: GameEngine, _prev_choices):
    narration = format_narration(result)
    if result.is_ending:
        icon = "⚰️" if result.ending_id in ("sinking_into_the_deep", "sanity_break") else "🌅"
        narration += f"\n\n---\n\n**{icon} {result.ending_id.replace('_', ' ').title()}**\n\n{result.ending_text}"

    sanity_html = format_sanity_bar(engine)
    status = format_status(engine)
    timeline = engine.get_event_timeline()

    choices = result.choices or []
    btn_labels = [
        choices[i]["text"] if i < len(choices) else "---" for i in range(3)
    ]
    btn_interactive = [i < len(choices) for i in range(3)]

    state_data = engine.get_state_summary()

    return (
        narration,
        sanity_html,
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


def _no_change(engine, choices_data):
    return (
        gr.update(),
        gr.update(),
        gr.update(),
        gr.update(),
        gr.update(),
        gr.update(),
        gr.update(),
        gr.update(),
        gr.update(),
        gr.update(),
        gr.update(),
        gr.update(),
        choices_data,
    )


if __name__ == "__main__":
    app = create_app()
    app.launch(share=False)
