from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.consistency.hard_rules import HardRulesChecker
from src.consistency.soft_checker import SoftChecker
from src.game.event_system import EventSystem, Event
from src.llm.client import LLMClient
from src.llm.output_parser import ParsedOutput, parse_llm_output
from src.llm.prompt_builder import PromptBuilder
from src.state.game_state import GameState
from src.state.loop_memory import LoopMemory

logger = logging.getLogger(__name__)

AUTO_TRUST_PER_INTERACTION = 5
TIME_PER_TURN = 30


@dataclass
class TurnResult:
    narration: str = ""
    dialogue_speaker: str | None = None
    dialogue_text: str | None = None
    choices: list[dict[str, Any]] = field(default_factory=list)
    intent: str = "UNKNOWN"
    sanity_delta: int = 0
    state_logs: list[str] = field(default_factory=list)
    consistency_log: str = ""
    event_triggered: str = ""
    is_ending: bool = False
    ending_id: str = ""
    ending_text: str = ""
    error: str = ""


class GameEngine:
    """Main game loop: events + LLM + state + consistency."""

    def __init__(
        self,
        config_dir: str = "config",
        data_dir: str = "data",
        log_dir: str = "logs",
    ):
        self.config_dir = Path(config_dir)
        self.data_dir = Path(data_dir)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        settings = self._load_settings()
        llm_cfg = settings.get("llm", {})
        consistency_cfg = settings.get("consistency", {})

        self.llm = LLMClient(
            model=llm_cfg.get("model", "gpt-4o-mini"),
            temperature=llm_cfg.get("temperature", 0.8),
            max_tokens=llm_cfg.get("max_tokens", 1024),
            base_url=llm_cfg.get("base_url") or None,
        )
        self.prompt_builder = PromptBuilder(config_dir)
        self.hard_checker = HardRulesChecker()
        self.soft_checker = SoftChecker(
            model_name=consistency_cfg.get("embedding_model", "all-MiniLM-L6-v2")
        )
        self.max_retries = consistency_cfg.get("max_retries", 2)

        events_path = self.data_dir / "scenarios" / "events.yaml"
        self.event_system = EventSystem(events_path) if events_path.exists() else None

        self.game_state: GameState | None = None
        self.loop_memory = LoopMemory()
        self._trajectory: list[dict] = []

    def _load_settings(self) -> dict:
        import yaml
        settings_path = self.config_dir / "settings.yaml"
        if settings_path.exists():
            with open(settings_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    # ------------------------------------------------------------------
    # Game lifecycle
    # ------------------------------------------------------------------

    def new_game(self) -> TurnResult:
        self.game_state = GameState.from_world_data(
            self.data_dir / "scenarios" / "world.yaml",
            self.data_dir / "scenarios" / "npcs.yaml",
        )
        self.loop_memory = LoopMemory()
        self._trajectory = []
        if self.event_system:
            self.event_system.reset_for_new_loop(self.loop_memory)

        event = self.event_system.check_events(
            self.game_state, self.loop_memory
        ) if self.event_system else None

        if event:
            return self._apply_event(event)
        return self._generate_opening()

    def new_loop(self) -> TurnResult:
        if self.game_state:
            self.loop_memory.record_loop_end(self.game_state)

        self.game_state = GameState.from_world_data(
            self.data_dir / "scenarios" / "world.yaml",
            self.data_dir / "scenarios" / "npcs.yaml",
        )
        self.game_state.loop_count = self.loop_memory.total_loops + 1
        self.game_state.sanity = min(100, 100 - max(0, self.loop_memory.total_loops * 5))
        self.game_state.discovered_facts = list(self.loop_memory.discovered_facts)

        if self.event_system:
            self.event_system.reset_for_new_loop(self.loop_memory)

        event = self.event_system.check_events(
            self.game_state, self.loop_memory
        ) if self.event_system else None

        if event:
            return self._apply_event(event)
        return self._generate_opening()

    # ------------------------------------------------------------------
    # Event system
    # ------------------------------------------------------------------

    def _apply_event(self, event: Event) -> TurnResult:
        """Apply a scripted event directly -- no LLM call needed."""
        if not self.game_state:
            return TurnResult(error="No active game.")

        state_logs = self.game_state.apply_state_updates(event.effects)
        sanity_delta = event.sanity_impact
        self.game_state.modify_sanity(sanity_delta)
        self.game_state.advance_time(TIME_PER_TURN)

        self.game_state.add_turn_to_history({
            "player_input": f"[EVENT: {event.id}]",
            "intent": "EVENT",
            "narration": event.narration[:150],
        })

        result = TurnResult(
            narration=event.narration,
            dialogue_speaker=event.dialogue.get("speaker") if event.dialogue else None,
            dialogue_text=event.dialogue.get("text") if event.dialogue else None,
            choices=event.choices if event.choices else [
                {"id": "continue", "text": "Continue", "sanity_cost": 0},
            ],
            intent="EVENT",
            sanity_delta=sanity_delta,
            state_logs=state_logs,
            event_triggered=event.title_zh,
        )

        ending = self._check_endings()
        if ending:
            result.is_ending = True
            result.ending_id = ending["id"]
            result.ending_text = ending["narration"]
            self.loop_memory.record_ending(ending["id"])

        return result

    # ------------------------------------------------------------------
    # Turn processing
    # ------------------------------------------------------------------

    def process_turn(self, player_input: str) -> TurnResult:
        if not self.game_state:
            return TurnResult(error="No active game. Call new_game() first.")

        self.game_state.turn += 1

        if self.game_state.is_midnight:
            return self._handle_midnight()

        # --- Check scripted events first ---
        if self.event_system:
            event = self.event_system.check_events(
                self.game_state, self.loop_memory, player_input
            )
            if event:
                return self._apply_event(event)

        # --- Auto trust: interacting with NPCs at your location ---
        self._auto_trust_gain(player_input)

        # --- LLM generation for non-event turns ---
        system_prompt = self.prompt_builder.build_system_prompt(
            self.game_state, self.loop_memory
        )
        user_msg = self.prompt_builder.build_user_message(player_input)

        parsed = None
        consistency_log_parts = []

        for attempt in range(1 + self.max_retries):
            try:
                raw = self.llm.chat(
                    system_prompt,
                    user_msg if attempt == 0 else self._build_retry_message(
                        user_msg, consistency_log_parts[-1]
                    ),
                    response_format={"type": "json_object"},
                )
                parsed = parse_llm_output(raw)

                if parsed.parse_errors:
                    consistency_log_parts.append(
                        f"Parse issues: {'; '.join(parsed.parse_errors)}"
                    )
                    if not parsed.is_valid:
                        continue

                violations = self.hard_checker.check(
                    self.game_state,
                    parsed.narration,
                    parsed.dialogue,
                    parsed.state_updates,
                )

                if violations:
                    violation_text = self.hard_checker.format_violations(violations)
                    consistency_log_parts.append(violation_text)
                    critical = [v for v in violations if v.severity == "critical"]
                    if critical and attempt < self.max_retries:
                        continue

                soft_issues = self.soft_checker.check(
                    parsed.narration,
                    self.game_state.discovered_facts,
                )
                if soft_issues:
                    consistency_log_parts.append(
                        self.soft_checker.format_issues(soft_issues)
                    )

                break

            except Exception as e:
                logger.error("Turn processing attempt %d failed: %s", attempt + 1, e)
                consistency_log_parts.append(f"Error on attempt {attempt + 1}: {e}")

        if parsed is None or not parsed.narration:
            return TurnResult(
                narration="Something feels wrong. The world shimmers for a moment, then steadies.",
                choices=[
                    {"id": "try_again", "text": "Shake it off and try again", "sanity_cost": 0},
                    {"id": "wait", "text": "Wait and observe", "sanity_cost": 0},
                    {"id": "leave", "text": "Leave this place", "sanity_cost": 0},
                ],
                consistency_log="\n".join(consistency_log_parts),
                error="Failed to get valid LLM response",
            )

        self._apply_parsed_output(parsed)
        self._log_turn(player_input, parsed)

        result = self._build_turn_result(parsed)
        result.consistency_log = "\n".join(consistency_log_parts)

        ending = self._check_endings()
        if ending:
            result.is_ending = True
            result.ending_id = ending["id"]
            result.ending_text = ending["narration"]
            self.loop_memory.record_ending(ending["id"])

        if self.game_state.sanity <= 0:
            result.is_ending = True
            result.ending_id = "sanity_break"
            result.ending_text = (
                "The last thread of reason snaps. The whispers are not whispers "
                "anymore -- they are the only sound that has ever existed. You open "
                "your mouth to scream and the sea rushes in to fill the silence."
            )

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _auto_trust_gain(self, player_input: str) -> None:
        """Every interaction at an NPC's location grants a small trust boost."""
        if not self.game_state:
            return
        for npc_id, npc in self.game_state.characters.items():
            if npc.location == self.game_state.location and npc.alive:
                self.game_state.update_trust(npc_id, AUTO_TRUST_PER_INTERACTION)

    def _apply_parsed_output(self, parsed: ParsedOutput) -> None:
        if not self.game_state:
            return
        self.game_state.modify_sanity(parsed.sanity_impact)
        self.game_state.advance_time(parsed.time_advance)
        self.game_state.apply_state_updates(parsed.state_updates)

        self.game_state.add_turn_to_history({
            "player_input": "action",
            "intent": parsed.intent,
            "narration": parsed.narration[:150],
        })

    def _build_turn_result(self, parsed: ParsedOutput) -> TurnResult:
        return TurnResult(
            narration=parsed.narration,
            dialogue_speaker=parsed.dialogue.get("speaker"),
            dialogue_text=parsed.dialogue.get("text"),
            choices=parsed.choices,
            intent=parsed.intent,
            sanity_delta=parsed.sanity_impact,
        )

    def _build_retry_message(self, original_msg: str, violation_text: str) -> str:
        return (
            f"{original_msg}\n\n"
            f"IMPORTANT: Your previous response had consistency issues:\n"
            f"{violation_text}\n"
            f"Please regenerate, fixing these problems."
        )

    def _generate_opening(self) -> TurnResult:
        system_prompt, user_msg = self.prompt_builder.build_opening_prompt(
            self.game_state, self.loop_memory
        )
        try:
            raw_response = self.llm.chat(
                system_prompt, user_msg,
                response_format={"type": "json_object"},
            )
            parsed = parse_llm_output(raw_response)
            self._apply_parsed_output(parsed)
            return self._build_turn_result(parsed)
        except Exception as e:
            logger.error("Opening generation failed: %s", e)
            return TurnResult(
                narration=self._fallback_opening(),
                choices=[
                    {"id": "explore_inn", "text": "Look around the inn", "sanity_cost": 0},
                    {"id": "talk_martha", "text": "Talk to the innkeeper", "sanity_cost": 0},
                    {"id": "go_outside", "text": "Step outside into the night", "sanity_cost": 0},
                ],
                error=str(e),
            )

    def _fallback_opening(self) -> str:
        if self.loop_memory.total_loops == 0:
            return (
                "You step off the evening coach into Ravenhollow. The salt wind bites "
                "at your collar. Before you stands the Sea Breeze Inn, its windows "
                "glowing with warm lamplight."
            )
        return (
            "You're standing at the inn's doorstep again. The same salt wind. The same "
            "lamplight. The same letter in your pocket. How many times now?"
        )

    def _handle_midnight(self) -> TurnResult:
        return TurnResult(
            narration=(
                "The church bells begin to toll. One. Two. Three... The sound "
                "reverberates through your skull, each strike erasing the world a "
                "little more. The streets dissolve. The buildings fold inward. "
                "Midnight. The loop closes. And then -- dusk. The salt wind. "
                "The letter in your pocket. Again."
            ),
            choices=[],
            is_ending=False,
        )

    def _check_endings(self) -> dict | None:
        if not self.game_state:
            return None

        import yaml
        plot_path = self.data_dir / "scenarios" / "plot_graph.yaml"
        if not plot_path.exists():
            return None

        with open(plot_path, "r", encoding="utf-8") as f:
            plot = yaml.safe_load(f)

        state = self.game_state
        endings = plot.get("endings", {})

        if (
            state.location == "caves"
            and not state.has_item("ritual_candle")
            and not state.has_item("lighthouse_lens")
        ):
            return endings.get("bad_end")

        if (
            state.flags.get("morrison_allied")
            and state.has_item("ritual_candle")
            and state.location == "caves"
            and not state.flags.get("eleanor_ritual_known")
        ):
            return endings.get("normal_end")

        if (
            state.flags.get("eleanor_ritual_known")
            and state.has_item("lighthouse_lens")
            and "elias_alternative_method" in state.discovered_facts
            and state.location == "caves"
            and state.sanity <= 40
        ):
            return endings.get("true_end")

        return None

    def _log_turn(self, player_input: str, parsed: ParsedOutput) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "loop": self.game_state.loop_count if self.game_state else 0,
            "turn": self.game_state.turn if self.game_state else 0,
            "player_input": player_input,
            "intent": parsed.intent,
            "narration": parsed.narration,
            "sanity": self.game_state.sanity if self.game_state else 0,
            "location": self.game_state.location if self.game_state else "",
            "state_updates": parsed.state_updates,
        }
        self._trajectory.append(entry)

        log_file = self.log_dir / f"trajectory_{datetime.now().strftime('%Y%m%d')}.jsonl"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error("Failed to write trajectory log: %s", e)

    def get_state_summary(self) -> dict:
        if not self.game_state:
            return {}
        return {
            "game_state": self.game_state.to_dict(),
            "loop_memory": self.loop_memory.to_dict(),
        }

    def get_event_timeline(self) -> str:
        if not self.event_system or not self.game_state:
            return ""
        return self.event_system.format_timeline(self.game_state)

    def get_event_timeline_html(self) -> str:
        if not self.event_system or not self.game_state:
            return ""
        return self.event_system.format_timeline_html(self.game_state)
