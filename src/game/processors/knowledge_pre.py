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
            examples = (
                "\n语义匹配示例（按意思匹配，不要求原文一致）：\n"
                "  知识: thomas_whispers（托马斯听到了海中的歌声）\n"
                '  玩家说「他消失前是不是听到了什么奇怪的声音？」→ 匹配 intensity=allusion\n'
                '  玩家说「我知道托马斯在海边听到了某种歌声」→ 匹配 intensity=direct\n'
                '  玩家说「告诉我托马斯那天晚上到底听到了什么！」→ 匹配 intensity=confrontation\n'
                "关键：只要语义相关就应匹配，无需使用原文关键词。"
            )
        else:
            header = (
                "--- AVAILABLE CROSS-LOOP KNOWLEDGE ---\n"
                "The player carries fragmented memories from previous loops. If they "
                "reference any of the following (even with different wording), include "
                "the ID and intensity in knowledge_triggered.\n"
                "NPCs marked * are at the current location."
            )
            examples = (
                "\nSemantic matching examples (match by MEANING, not exact words):\n"
                "  Knowledge: thomas_whispers (Thomas heard singing from the sea)\n"
                '  Player says "Did he hear anything strange before disappearing?" → MATCH intensity=allusion\n'
                '  Player says "I know Thomas heard some kind of song by the water" → MATCH intensity=direct\n'
                '  Player says "Tell me what Thomas really heard that night!" → MATCH intensity=confrontation\n'
                "Key: Different phrasing still counts if the meaning relates to the knowledge."
            )

        ctx.extra_prompt_parts.append(header + "\n" + "\n".join(lines) + examples)

        # Fast-path keyword matching (cheap, catches obvious hits)
        for key in available:
            if key.id in lm.used_knowledge:
                continue
            if key.matches_input(ctx.player_input):
                ctx.keyword_hits.append(key.id)
                logger.debug("Keyword fast-path hit: %s", key.id)

        return None
