"""PreCheckProcessor: sanity/trust application, hallucination resolution, midnight."""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

from src.game.game_data import (
    HALLUCINATION_CHOICES,
    HALLUCINATION_IDS,
    HALLUCINATION_NARRATIONS,
)

if TYPE_CHECKING:
    from src.game.engine import TurnResult
    from src.game.event_system import EventSystem
    from src.game.turn_context import TurnContext

logger = logging.getLogger(__name__)


class PreCheckProcessor:

    def __init__(self, event_system: "EventSystem | None", cfg_time_per_turn: int):
        self._event_system = event_system
        self._cfg_time_per_turn = cfg_time_per_turn

    def process(self, ctx: "TurnContext") -> "TurnResult | None":
        from src.game.engine import TurnResult

        gs = ctx.game_state

        if ctx.choice_sanity_cost:
            gs.modify_sanity(ctx.choice_sanity_cost)

        if ctx.trust_bonus:
            self._apply_trust_bonus(ctx)

        if ctx.choice_id in HALLUCINATION_IDS:
            return self._resolve_hallucination(ctx)

        if self._event_system and ctx.choice_id:
            self._event_system.last_choice_id = ctx.choice_id

        gs.turn += 1

        if gs.is_midnight:
            return self._handle_midnight(ctx)

        return None

    # ------------------------------------------------------------------

    @staticmethod
    def _apply_trust_bonus(ctx: "TurnContext") -> None:
        gs = ctx.game_state
        for npc_id, delta in (ctx.trust_bonus or {}).items():
            if npc_id in gs.characters:
                gs.update_trust(npc_id, delta)
                logger.info("trust_bonus: %s +%d", npc_id, delta)

    def _resolve_hallucination(self, ctx: "TurnContext") -> "TurnResult":
        from src.game.engine import TurnResult

        gs = ctx.game_state
        gs.turn += 1
        gs.advance_time(self._cfg_time_per_turn)

        pool = HALLUCINATION_NARRATIONS.get(ctx.lang, HALLUCINATION_NARRATIONS["en"])
        narration = random.choice(pool)
        zh = ctx.lang == "zh"
        return TurnResult(
            narration=narration,
            choices=[
                {"id": "shake_off", "text": "摇摇头，回到现实" if zh else "Shake it off", "sanity_cost": 0},
                {"id": "wait", "text": "停下来观察" if zh else "Wait and observe", "sanity_cost": 0},
                {"id": "leave", "text": "离开这里" if zh else "Leave this place", "sanity_cost": 0},
            ],
            intent="SPECIAL",
            sanity_delta=ctx.choice_sanity_cost,
        )

    def _handle_midnight(self, ctx: "TurnContext") -> "TurnResult":
        from src.game.engine import TurnResult
        from src.game.game_data import NARRATIVE_HOOKS

        gs = ctx.game_state
        lang = ctx.lang
        lm = ctx.loop_memory

        base = (
            "教堂钟声响起。一下。两下。三下……声波穿透你的头骨，每一击都在抹去"
            "更多的世界。街道溶解。建筑向内折叠。午夜。循环闭合。然后——黄昏。"
            "咸涩的海风。口袋里的信。又一次。"
        ) if lang == "zh" else (
            "The church bells begin to toll. One. Two. Three... The sound "
            "reverberates through your skull, each strike erasing the world a "
            "little more. The streets dissolve. The buildings fold inward. "
            "Midnight. The loop closes. And then -- dusk. The salt wind. "
            "The letter in your pocket. Again."
        )
        hints = _build_loop_hints(gs, lm, lang)
        narration = f"{base}\n\n{hints}" if hints else base

        continue_text = "闭上眼，让循环带你回去" if lang == "zh" else "Close your eyes and let the loop take you"
        return TurnResult(
            narration=narration,
            choices=[{"id": "restart_loop", "text": continue_text, "sanity_cost": 0}],
            is_ending=False,
            is_loop_reset=True,
        )


def _build_loop_hints(gs, lm, lang: str) -> str:
    """Generate diegetic narrative memories instead of GPS-style hints."""
    from src.game.game_data import NARRATIVE_HOOKS

    hints: list[str] = []
    visited = gs.flags.get("_visited_locations", [])
    if not isinstance(visited, list):
        visited = []

    for hook in NARRATIVE_HOOKS:
        req_fact = hook.get("requires_fact", "")
        if req_fact and req_fact not in gs.discovered_facts:
            continue
        target_loc = hook.get("target_location")
        target_npc = hook.get("target_npc")
        if target_loc and target_loc in visited:
            continue
        if target_npc:
            npc = gs.characters.get(target_npc)
            if npc and npc.met:
                continue
        hints.append(hook.get(lang, hook.get("en", "")))

    unused_keys = lm.unused_knowledge
    for key in unused_keys[:2]:
        hint_text = key.hint_zh if lang == "zh" else key.hint_en
        if hint_text:
            prefix = "你隐约记得" if lang == "zh" else "You dimly recall"
            hints.append(f"{prefix}: {hint_text}")

    if not hints:
        return ""

    new_facts = len([f for f in gs.discovered_facts if f not in lm.discovered_facts])
    npcs_met = sum(1 for n in gs.characters.values() if n.met and n.alive)

    if lang == "zh":
        header = "─── 午夜的碎片 ───"
        summary = f"时间倒流之际，{new_facts} 条新线索和 {npcs_met} 张面孔在记忆中沉淀下来。"
        prefix = "残留的记忆如潮水般涌来："
    else:
        header = "--- Fragments at Midnight ---"
        summary = (
            f"As time unravels, {new_facts} new clue(s) and "
            f"{npcs_met} face(s) settle into memory."
        )
        prefix = "Echoes of this loop linger:"

    bullet = "\n".join(f"  \u25b8 {h}" for h in hints[:4])
    return f"{header}\n{summary}\n\n{prefix}\n{bullet}"
