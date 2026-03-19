"""PostEventProcessor: secondary event check after LLM output + location inference."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.game.game_data import LOCATION_KEYWORDS

if TYPE_CHECKING:
    from src.game.engine import GameEngine, TurnResult
    from src.game.turn_context import TurnContext

logger = logging.getLogger(__name__)


class PostEventProcessor:

    def __init__(self, engine: "GameEngine"):
        self._engine = engine

    def process(self, ctx: "TurnContext") -> "TurnResult | None":
        parsed = ctx.parsed
        if parsed is None:
            return None

        gs = ctx.game_state
        _infer_location_from_input(gs, ctx.player_input, parsed)
        self._engine._log_turn(ctx.player_input, parsed)

        es = self._engine.event_system
        if es and parsed.entities:
            entity_text = " ".join(str(v) for v in parsed.entities.values() if v)
            combined_input = f"{ctx.player_input} {entity_text}"
            late_event = es.check_events(gs, ctx.loop_memory, combined_input)
            if late_event:
                event_result = self._engine._apply_event(late_event, advance_time=False)
                event_result.consistency_log = "\n".join(ctx.consistency_log_parts)
                return event_result

        return None


def _infer_location_from_input(gs, player_input: str, parsed) -> bool:
    """Fallback: if the LLM forgot move_player, infer location from input + entities."""
    if any(u.get("type") == "move_player" for u in parsed.state_updates):
        return False

    entity_loc = (parsed.entities or {}).get("location", "")
    combined = f"{player_input} {entity_loc}".lower()

    for loc_id, keywords in LOCATION_KEYWORDS:
        if loc_id == gs.location:
            continue
        if any(kw in combined for kw in keywords):
            logger.info("Auto-inferred move_player to %s (LLM omitted it)", loc_id)
            gs.move_player(loc_id)
            return True
    return False
