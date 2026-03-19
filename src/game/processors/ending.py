"""EndingProcessor: ending checks, sanity-death, hallucination injection, result building."""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import TYPE_CHECKING

from src.game.game_data import HALLUCINATION_CHOICES

if TYPE_CHECKING:
    from src.game.engine import TurnResult
    from src.game.turn_context import TurnContext

logger = logging.getLogger(__name__)


class EndingProcessor:

    def __init__(self, data_dir: str | Path):
        self._data_dir = Path(data_dir)

    def process(self, ctx: "TurnContext") -> "TurnResult":
        from src.game.engine import TurnResult

        parsed = ctx.parsed
        if parsed is None:
            return TurnResult(error="No parsed output available.")

        gs = ctx.game_state
        choices = _inject_hallucination_choice(gs, parsed.choices, ctx.lang)

        result = TurnResult(
            narration=parsed.narration,
            dialogue_speaker=parsed.dialogue.get("speaker"),
            dialogue_text=parsed.dialogue.get("text"),
            choices=choices,
            intent=parsed.intent,
            sanity_delta=parsed.sanity_impact,
            consistency_log="\n".join(ctx.consistency_log_parts),
            knowledge_used=ctx.knowledge_hits,
            player_input=ctx.player_input,
        )

        ending = _check_endings(gs, self._data_dir)
        if ending:
            result.is_ending = True
            result.ending_id = ending["id"]
            result.ending_text = ending["narration"]
            ctx.loop_memory.record_ending(ending["id"])

        if gs.sanity <= 0:
            result.is_ending = True
            result.ending_id = "sanity_break"
            result.ending_text = (
                "The last thread of reason snaps. The whispers are not whispers "
                "anymore -- they are the only sound that has ever existed. You open "
                "your mouth to scream and the sea rushes in to fill the silence."
            )

        return result


def _inject_hallucination_choice(gs, choices: list[dict], lang: str) -> list[dict]:
    """At low sanity, inject a phantom choice that wastes time and drains sanity."""
    level = gs.sanity_level
    if level in ("lucid", "uneasy"):
        return choices

    prob = 0.4 if level == "distorted" else 0.7
    if random.random() > prob:
        return choices

    pool = HALLUCINATION_CHOICES.get(lang, HALLUCINATION_CHOICES["en"])
    existing_ids = {c.get("id") for c in choices}
    candidates = [c for c in pool if c["id"] not in existing_ids]
    if not candidates:
        return choices

    phantom = dict(random.choice(candidates))
    phantom["_hallucination"] = True
    insert_pos = random.randint(0, min(2, len(choices)))
    choices = list(choices)
    choices.insert(insert_pos, phantom)
    return choices[:4]


def _check_endings(gs, data_dir: Path) -> dict | None:
    import yaml

    plot_path = data_dir / "scenarios" / "plot_graph.yaml"
    if not plot_path.exists():
        return None

    with open(plot_path, "r", encoding="utf-8") as f:
        plot = yaml.safe_load(f)

    endings = plot.get("endings", {})

    if (
        gs.location == "caves"
        and not gs.has_item("ritual_candle")
        and not gs.has_item("lighthouse_lens")
    ):
        return endings.get("bad_end")

    if (
        gs.flags.get("morrison_allied")
        and gs.has_item("ritual_candle")
        and gs.location == "caves"
        and not gs.flags.get("eleanor_ritual_known")
    ):
        return endings.get("normal_end")

    if (
        gs.flags.get("eleanor_ritual_known")
        and gs.has_item("lighthouse_lens")
        and "elias_found_alternative_method" in gs.discovered_facts
        and gs.location == "caves"
        and gs.sanity <= 40
    ):
        return endings.get("true_end")

    return None
