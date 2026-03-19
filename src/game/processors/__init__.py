"""Turn processors: each handles one concern of process_turn."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.game.engine import TurnResult
    from src.game.turn_context import TurnContext


class TurnProcessor(Protocol):
    """A single step in the turn-processing pipeline.

    Return a TurnResult to short-circuit (skip remaining processors).
    Return None to continue to the next processor.
    """

    def process(self, ctx: TurnContext) -> TurnResult | None: ...
