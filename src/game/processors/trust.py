"""TrustProcessor: auto-trust gain and fact-based trust bonuses."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.game.game_data import FACT_TRUST_MAP
from src.state.game_state import SANITY_EFFECTS

if TYPE_CHECKING:
    from src.game.engine import TurnResult
    from src.game.turn_context import TurnContext

logger = logging.getLogger(__name__)


class TrustProcessor:

    def process(self, ctx: "TurnContext") -> "TurnResult | None":
        gs = ctx.game_state

        fx = SANITY_EFFECTS.get(gs.sanity_level, SANITY_EFFECTS["lucid"])
        trust_mod = fx["trust_mod"]
        for npc_id, npc in gs.characters.items():
            if npc.location == gs.location and npc.alive:
                gs.update_trust(npc_id, trust_mod)

        _apply_fact_trust_bonus(gs)
        return None


def _apply_fact_trust_bonus(gs) -> None:
    """Grant one-time trust when the player carries relevant facts to an NPC."""
    player_facts = set(gs.discovered_facts)
    for npc_id, npc in gs.characters.items():
        if npc.location != gs.location or not npc.alive:
            continue
        fact_map = FACT_TRUST_MAP.get(npc_id, {})
        for fact_id, bonus in fact_map.items():
            if fact_id not in player_facts:
                continue
            flag_key = f"_fact_trust_{npc_id}_{fact_id}"
            if gs.flags.get(flag_key):
                continue
            gs.set_flag(flag_key, True)
            gs.update_trust(npc_id, bonus)
            logger.info("fact_trust_bonus: %s +%d (fact=%s)", npc_id, bonus, fact_id)
