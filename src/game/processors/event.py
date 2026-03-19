"""EventProcessor: check and apply scripted events before LLM call."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.game.engine import GameEngine, TurnResult
    from src.game.turn_context import TurnContext


class EventProcessor:

    def __init__(self, engine: "GameEngine"):
        self._engine = engine

    def process(self, ctx: "TurnContext") -> "TurnResult | None":
        es = self._engine.event_system
        if not es:
            return None

        event = es.check_events(ctx.game_state, ctx.loop_memory, ctx.player_input)
        if event:
            es.last_choice_id = ""
            return self._engine._apply_event(event)
        es.last_choice_id = ""
        return None
