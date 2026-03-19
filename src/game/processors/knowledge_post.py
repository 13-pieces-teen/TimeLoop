"""KnowledgePostProcessor: resolve knowledge usage after the LLM call.

Merges LLM-detected ``knowledge_triggered`` with keyword fast-path hits,
validates against available knowledge, and settles trust changes based on
intensity (allusion / direct / confrontation).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.state.loop_memory import KnowledgeKey

if TYPE_CHECKING:
    from src.game.engine import TurnResult
    from src.game.turn_context import TurnContext

logger = logging.getLogger(__name__)


class KnowledgePostProcessor:

    def process(self, ctx: "TurnContext") -> "TurnResult | None":
        gs = ctx.game_state
        lm = ctx.loop_memory

        if lm.total_loops == 0:
            return None

        available_map: dict[str, KnowledgeKey] = {
            k.id: k for k in lm.knowledge_keys
        }
        if not available_map:
            return None

        # --- Merge LLM detections + keyword fast-path ---
        merged: dict[str, str] = {}  # knowledge_id -> intensity

        llm_hits = ctx.parsed.knowledge_triggered if ctx.parsed else []
        for hit in llm_hits:
            kid = hit.get("id", "")
            intensity = hit.get("intensity", "direct")
            if kid in available_map:
                merged[kid] = intensity

        for kid in ctx.keyword_hits:
            if kid not in merged and kid in available_map:
                merged[kid] = "direct"

        if not merged:
            return None

        npcs_here = [
            npc_id for npc_id, npc in gs.characters.items()
            if npc.location == gs.location and npc.alive
        ]

        results: list[dict] = []
        for kid, intensity in merged.items():
            key = available_map[kid]

            if key.id in lm.used_knowledge and KnowledgeKey.consumes(intensity):
                continue
            if key.id in lm.used_knowledge and not KnowledgeKey.consumes(intensity):
                # allusion on already-used knowledge — no further reward
                continue

            correct_npc_here = key.target_npc in npcs_here
            if correct_npc_here:
                reward = key.reward_for(intensity)
                gs.update_trust(key.target_npc, reward)
                if KnowledgeKey.consumes(intensity):
                    lm.mark_knowledge_used(key.id)
                results.append({
                    "knowledge_id": key.id,
                    "npc_id": key.target_npc,
                    "trust_delta": reward,
                    "correct_target": True,
                    "intensity": intensity,
                })
                logger.info(
                    "Knowledge used: %s (%s) on %s → trust +%d",
                    key.id, intensity, key.target_npc, reward,
                )
            else:
                penalty = key.trust_penalty_wrong_npc
                for npc_id in npcs_here:
                    gs.update_trust(npc_id, penalty)
                results.append({
                    "knowledge_id": key.id,
                    "npc_id": npcs_here[0] if npcs_here else "none",
                    "trust_delta": penalty,
                    "correct_target": False,
                    "intensity": intensity,
                })
                if KnowledgeKey.consumes(intensity):
                    lm.mark_knowledge_used(key.id)
                logger.info(
                    "Knowledge misused: %s (%s) on %s → trust %d",
                    key.id, intensity,
                    npcs_here[0] if npcs_here else "none", penalty,
                )

        ctx.knowledge_hits = results
        return None
