"""KnowledgePreProcessor: inject available knowledge descriptions into prompt
and perform fast-path keyword matching before the LLM call."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.game.engine import TurnResult
    from src.game.turn_context import TurnContext

logger = logging.getLogger(__name__)


class KnowledgePreProcessor:

    def process(self, ctx: "TurnContext") -> "TurnResult | None":
        lm = ctx.loop_memory
        gs = ctx.game_state

        if lm.total_loops == 0:
            return None

        available = lm.knowledge_keys
        if not available:
            return None

        npcs_here = [
            npc_id for npc_id, npc in gs.characters.items()
            if npc.location == gs.location and npc.alive
        ]

        lang = ctx.lang
        desc_key = "description_zh" if lang == "zh" else "description_en"

        lines: list[str] = []
        for key in available:
            desc = getattr(key, desc_key, key.description_en)
            target_label = key.target_npc
            here_marker = " *" if key.target_npc in npcs_here else ""
            lines.append(f"- {key.id}: {desc} [target: {target_label}{here_marker}]")

        if not lines:
            return None

        if lang == "zh":
            header = (
                "--- 可用跨循环知识 ---\n"
                "玩家携带着前世记忆的碎片。如果玩家引用了以下任何一条（即使措辞不同），"
                "请在 knowledge_triggered 中标注对应 ID 和强度。\n"
                "标 * 的NPC在当前位置。"
            )
        else:
            header = (
                "--- AVAILABLE CROSS-LOOP KNOWLEDGE ---\n"
                "The player carries fragmented memories from previous loops. If they "
                "reference any of the following (even with different wording), include "
                "the ID and intensity in knowledge_triggered.\n"
                "NPCs marked * are at the current location."
            )

        ctx.extra_prompt_parts.append(header + "\n" + "\n".join(lines))

        # Fast-path keyword matching (cheap, catches obvious hits)
        for key in available:
            if key.id in lm.used_knowledge:
                continue
            if key.matches_input(ctx.player_input):
                ctx.keyword_hits.append(key.id)
                logger.debug("Keyword fast-path hit: %s", key.id)

        return None
