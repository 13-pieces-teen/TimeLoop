"""TurnContext: mutable context bag passed through the processor chain."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.game.engine import TurnResult
    from src.llm.output_parser import ParsedOutput
    from src.state.game_state import GameState
    from src.state.loop_memory import LoopMemory


@dataclass
class TurnContext:
    """Carries all state needed by turn processors and accumulates results."""

    player_input: str
    choice_id: str
    choice_sanity_cost: int
    trust_bonus: dict[str, int] | None

    game_state: GameState
    loop_memory: LoopMemory
    lang: str

    consistency_log_parts: list[str] = field(default_factory=list)
    knowledge_hits: list[dict] = field(default_factory=list)
    keyword_hits: list[str] = field(default_factory=list)
    extra_prompt_parts: list[str] = field(default_factory=list)

    parsed: ParsedOutput | None = field(default=None, repr=False)
