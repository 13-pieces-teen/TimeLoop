"""LLMProcessor: prompt construction, LLM call with retry, consistency checks."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from src.game.game_data import compute_ambient_sanity_drain
from src.llm.output_parser import parse_llm_output
from src.state.game_state import SANITY_EFFECTS

if TYPE_CHECKING:
    from src.consistency.hard_rules import HardRulesChecker
    from src.consistency.soft_checker import SoftChecker
    from src.game.engine import TurnResult
    from src.game.event_system import EventSystem
    from src.game.turn_context import TurnContext
    from src.llm.client import LLMClient
    from src.llm.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class LLMProcessor:

    def __init__(
        self,
        llm: "LLMClient",
        prompt_builder: "PromptBuilder",
        hard_checker: "HardRulesChecker",
        soft_checker: "SoftChecker | None",
        event_system: "EventSystem | None",
        max_retries: int,
        cfg_time_per_turn: int,
        get_cached_system: callable,
    ):
        self._llm = llm
        self._prompt_builder = prompt_builder
        self._hard_checker = hard_checker
        self._soft_checker = soft_checker
        self._event_system = event_system
        self._max_retries = max_retries
        self._cfg_time_per_turn = cfg_time_per_turn
        self._get_cached_system = get_cached_system

    def process(self, ctx: "TurnContext") -> "TurnResult | None":
        from src.game.engine import TurnResult

        gs = ctx.game_state

        system_prompt = self._get_cached_system()

        if self._event_system:
            narrative_hints = self._event_system.get_narrative_hints(
                gs, ctx.loop_memory, lang=ctx.lang,
            )
            if narrative_hints:
                ctx.extra_prompt_parts.append(narrative_hints)

        extra_context = "\n\n".join(ctx.extra_prompt_parts) if ctx.extra_prompt_parts else ""

        user_msg = self._prompt_builder.build_user_message(
            ctx.player_input, gs, ctx.loop_memory,
            ctx.lang, extra_context=extra_context,
        )

        parsed = None

        for attempt in range(1 + self._max_retries):
            try:
                raw = self._llm.chat(
                    system_prompt,
                    user_msg if attempt == 0 else _build_retry_message(
                        user_msg, ctx.consistency_log_parts[-1]
                    ),
                    response_format={"type": "json_object"},
                )
                parsed = parse_llm_output(raw)

                if parsed.parse_errors:
                    ctx.consistency_log_parts.append(
                        f"Parse issues: {'; '.join(parsed.parse_errors)}"
                    )
                    if not parsed.is_valid:
                        continue

                violations = self._hard_checker.check(
                    gs, parsed.narration, parsed.dialogue, parsed.state_updates,
                )
                if violations:
                    violation_text = self._hard_checker.format_violations(violations)
                    ctx.consistency_log_parts.append(violation_text)
                    critical = [v for v in violations if v.severity == "critical"]
                    if critical and attempt < self._max_retries:
                        continue

                if self._soft_checker:
                    _run_bg_soft_check(
                        self._soft_checker, parsed.narration,
                        list(gs.discovered_facts), ctx.consistency_log_parts,
                    )

                break

            except Exception as e:
                logger.error("Turn processing attempt %d failed: %s", attempt + 1, e)
                ctx.consistency_log_parts.append(f"Error on attempt {attempt + 1}: {e}")

        if parsed is None or not parsed.narration:
            return TurnResult(
                narration="Something feels wrong. The world shimmers for a moment, then steadies.",
                choices=[
                    {"id": "try_again", "text": "Shake it off and try again", "sanity_cost": 0},
                    {"id": "wait", "text": "Wait and observe", "sanity_cost": 0},
                    {"id": "leave", "text": "Leave this place", "sanity_cost": 0},
                ],
                consistency_log="\n".join(ctx.consistency_log_parts),
                error="Failed to get valid LLM response",
            )

        _apply_parsed_output(gs, parsed, self._cfg_time_per_turn)
        ctx.parsed = parsed
        return None


def _apply_parsed_output(gs, parsed, cfg_time_per_turn: int) -> None:
    # Hidden ambient drain — not reflected in TurnResult.sanity_delta
    ambient = compute_ambient_sanity_drain(gs.time_minutes, gs.location)
    gs.modify_sanity(ambient)

    gs.modify_sanity(parsed.sanity_impact)
    fx = SANITY_EFFECTS.get(gs.sanity_level, SANITY_EFFECTS["lucid"])
    capped_time = min(parsed.time_advance, cfg_time_per_turn)
    warped_time = int(capped_time * fx["time_warp"])
    gs.advance_time(warped_time)
    gs.apply_state_updates(parsed.state_updates)
    gs.add_turn_to_history({
        "player_input": "action",
        "intent": parsed.intent,
        "narration": parsed.narration[:150],
    })


def _build_retry_message(original_msg: str, violation_text: str) -> str:
    return (
        f"{original_msg}\n\n"
        f"IMPORTANT: Your previous response had consistency issues:\n"
        f"{violation_text}\n"
        f"Please regenerate, fixing these problems."
    )


def _run_bg_soft_check(checker, narration: str, facts: list, log_parts: list) -> None:
    def _bg(c, n, f, lp):
        issues = c.check(n, f)
        if issues:
            lp.append(c.format_issues(issues))
    threading.Thread(target=_bg, args=(checker, narration, facts, log_parts), daemon=True).start()
