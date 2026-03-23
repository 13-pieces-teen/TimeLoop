from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.consistency.hard_rules import HardRulesChecker
from src.consistency.soft_checker import SoftChecker
from src.game.event_system import EventSystem, Event
from src.game.game_data import (
    HALLUCINATION_CHOICES,
    TIME_PER_TURN,
    compute_ambient_sanity_drain,
)
from src.game.processors.ending import EndingProcessor, _check_endings, _inject_hallucination_choice
from src.game.processors.event import EventProcessor
from src.game.processors.knowledge_pre import KnowledgePreProcessor
from src.game.processors.knowledge_post import KnowledgePostProcessor
from src.game.processors.llm_call import LLMProcessor
from src.game.processors.post_event import PostEventProcessor
from src.game.processors.pre_check import PreCheckProcessor
from src.game.processors.trust import TrustProcessor
from src.game.turn_context import TurnContext
from src.llm.client import LLMClient
from src.llm.output_parser import ParsedOutput, parse_llm_output
from src.llm.prompt_builder import PromptBuilder
from src.state.game_state import GameState, SANITY_EFFECTS
from src.state.loop_memory import LoopMemory

logger = logging.getLogger(__name__)


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
    event_image: str | None = None
    is_ending: bool = False
    ending_id: str = ""
    ending_text: str = ""
    is_loop_reset: bool = False
    error: str = ""
    knowledge_used: list[dict] = field(default_factory=list)
    player_input: str = ""


class GameEngine:
    """Main game loop: events + LLM + state + consistency."""

    def __init__(
        self,
        config_dir: str = "config",
        data_dir: str = "data",
        log_dir: str = "logs",
        lang: str = "en",
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
        self.soft_check_enabled = consistency_cfg.get("soft_check", False)
        self.soft_checker = (
            SoftChecker(model_name=consistency_cfg.get("embedding_model", "all-MiniLM-L6-v2"))
            if self.soft_check_enabled else None
        )
        self.max_retries = consistency_cfg.get("max_retries", 1)

        game_cfg = settings.get("game", {})
        self.cfg_starting_sanity = game_cfg.get("starting_sanity", 100)
        self.cfg_sanity_cap = game_cfg.get("sanity_cap", 100)
        self.cfg_time_per_turn = game_cfg.get("time_per_turn_minutes", TIME_PER_TURN)

        events_path = self.data_dir / "scenarios" / "events.yaml"
        self.event_system = EventSystem(events_path) if events_path.exists() else None

        self.descriptions = self._load_descriptions()

        self.lang = lang
        self.game_state: GameState | None = None
        self.loop_memory = LoopMemory()
        self._trajectory: list[dict] = []

        self._cached_system: str | None = None
        self._cached_lang: str | None = None

        self._processors = self._build_pipeline()

    # ------------------------------------------------------------------
    # Pipeline assembly
    # ------------------------------------------------------------------

    def _build_pipeline(self) -> list:
        return [
            PreCheckProcessor(self.event_system, self.cfg_time_per_turn),
            EventProcessor(self),
            TrustProcessor(),
            KnowledgePreProcessor(),
            LLMProcessor(
                llm=self.llm,
                prompt_builder=self.prompt_builder,
                hard_checker=self.hard_checker,
                soft_checker=self.soft_checker,
                event_system=self.event_system,
                max_retries=self.max_retries,
                cfg_time_per_turn=self.cfg_time_per_turn,
                get_cached_system=self._get_cached_system,
            ),
            KnowledgePostProcessor(),
            PostEventProcessor(self),
            EndingProcessor(self.data_dir, world_data=self.prompt_builder.world_data),
        ]

    # ------------------------------------------------------------------
    # Prompt caching
    # ------------------------------------------------------------------

    def _get_cached_system(self) -> str:
        """Return Tier-1 static system prompt, rebuilding only when lang changes."""
        if self._cached_system is None or self._cached_lang != self.lang:
            self._cached_system = self.prompt_builder.build_static_system(self.lang)
            self._cached_lang = self.lang
        return self._cached_system

    def _load_settings(self) -> dict:
        import yaml
        settings_path = self.config_dir / "settings.yaml"
        if settings_path.exists():
            with open(settings_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _load_descriptions(self) -> dict:
        import yaml
        desc_path = self.data_dir / "scenarios" / "descriptions.yaml"
        if desc_path.exists():
            with open(desc_path, "r", encoding="utf-8") as f:
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

    SANITY_DECAY_PER_LOOP = 12
    TIME_DECAY_PER_LOOP = 15
    TRUST_CARRY_RATIO = 0.35

    def new_loop(self) -> TurnResult:
        if self.game_state:
            self.loop_memory.record_loop_end(self.game_state)

        self.game_state = GameState.from_world_data(
            self.data_dir / "scenarios" / "world.yaml",
            self.data_dir / "scenarios" / "npcs.yaml",
        )
        loops = self.loop_memory.total_loops
        self.game_state.loop_count = loops + 1
        cap = self.cfg_sanity_cap
        base = self.cfg_starting_sanity
        self.game_state.sanity = min(cap, base - max(0, loops * self.SANITY_DECAY_PER_LOOP))

        time_lost = min(120, loops * self.TIME_DECAY_PER_LOOP)
        self.game_state.time_minutes = time_lost

        self.game_state.discovered_facts = list(self.loop_memory.discovered_facts)

        for npc_id, npc in self.game_state.characters.items():
            prev_max = self.loop_memory.npc_max_trust.get(npc_id, 0)
            if prev_max > 0:
                npc.trust = int(prev_max * self.TRUST_CARRY_RATIO)

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

    def _apply_event(self, event: Event, advance_time: bool = True) -> TurnResult:
        """Apply a scripted event directly -- no LLM call needed."""
        if not self.game_state:
            return TurnResult(error="No active game.")

        lang = self.lang
        state_logs = self.game_state.apply_state_updates(event.effects)
        sanity_delta = event.sanity_impact
        self.game_state.modify_sanity(sanity_delta)
        if advance_time:
            cost = event.time_cost if event.time_cost is not None else self.cfg_time_per_turn
            self.game_state.advance_time(cost)

        narration = event.get_narration(lang)
        dialogue = event.get_dialogue(lang)
        choices = event.get_choices(lang)

        self.game_state.add_turn_to_history({
            "player_input": f"[EVENT: {event.id}]",
            "intent": "EVENT",
            "narration": narration[:150],
        })

        fallback_continue = "继续" if lang == "zh" else "Continue"
        result = TurnResult(
            narration=narration,
            dialogue_speaker=dialogue.get("speaker") if dialogue else None,
            dialogue_text=dialogue.get("text") if dialogue else None,
            choices=choices if choices else [
                {"id": "continue", "text": fallback_continue, "sanity_cost": 0},
            ],
            intent="EVENT",
            sanity_delta=sanity_delta,
            state_logs=state_logs,
            event_triggered=event.get_title(lang),
            event_image=event.image,
        )

        ending = _check_endings(self.game_state, self.data_dir)
        if ending:
            result.is_ending = True
            result.ending_id = ending["id"]
            result.ending_text = ending["narration"]
            self.loop_memory.record_ending(ending["id"])

        return result

    # ------------------------------------------------------------------
    # Turn processing (pipeline)
    # ------------------------------------------------------------------

    def process_turn(
        self,
        player_input: str,
        choice_sanity_cost: int = 0,
        choice_id: str = "",
        trust_bonus: dict[str, int] | None = None,
    ) -> TurnResult:
        if not self.game_state:
            return TurnResult(error="No active game. Call new_game() first.")

        ctx = TurnContext(
            player_input=player_input,
            choice_id=choice_id,
            choice_sanity_cost=choice_sanity_cost,
            trust_bonus=trust_bonus,
            game_state=self.game_state,
            loop_memory=self.loop_memory,
            lang=self.lang,
        )

        for processor in self._processors:
            result = processor.process(ctx)
            if result is not None:
                return result

        return TurnResult(error="Pipeline ended without producing a result.")

    # ------------------------------------------------------------------
    # Helpers (kept on engine for lifecycle / opening / logging)
    # ------------------------------------------------------------------

    def _generate_opening(self) -> TurnResult:
        system_prompt, user_msg = self.prompt_builder.build_opening_prompt(
            self.game_state, self.loop_memory, lang=self.lang,
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

    def _apply_parsed_output(self, parsed: ParsedOutput) -> None:
        if not self.game_state:
            return
        # Hidden ambient drain (opening turn)
        ambient = compute_ambient_sanity_drain(
            self.game_state.time_minutes, self.game_state.location,
        )
        self.game_state.modify_sanity(ambient)

        self.game_state.modify_sanity(parsed.sanity_impact)
        fx = SANITY_EFFECTS.get(self.game_state.sanity_level, SANITY_EFFECTS["lucid"])
        capped_time = min(parsed.time_advance, self.cfg_time_per_turn)
        warped_time = int(capped_time * fx["time_warp"])
        self.game_state.advance_time(warped_time)
        self.game_state.apply_state_updates(parsed.state_updates)
        self.game_state.add_turn_to_history({
            "player_input": "action",
            "intent": parsed.intent,
            "narration": parsed.narration[:150],
        })

    def _build_turn_result(self, parsed: ParsedOutput) -> TurnResult:
        choices = _inject_hallucination_choice(
            self.game_state, parsed.choices, self.lang,
        ) if self.game_state else parsed.choices
        return TurnResult(
            narration=parsed.narration,
            dialogue_speaker=parsed.dialogue.get("speaker"),
            dialogue_text=parsed.dialogue.get("text"),
            choices=choices,
            intent=parsed.intent,
            sanity_delta=parsed.sanity_impact,
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
        return self.event_system.format_timeline_html(self.game_state, lang=self.lang)
