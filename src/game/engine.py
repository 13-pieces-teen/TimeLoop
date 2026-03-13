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

AUTO_TRUST_PER_INTERACTION = 10
TIME_PER_TURN = 20


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
        self.soft_checker = SoftChecker(
            model_name=consistency_cfg.get("embedding_model", "all-MiniLM-L6-v2")
        )
        self.max_retries = consistency_cfg.get("max_retries", 2)

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

    def new_loop(self) -> TurnResult:
        if self.game_state:
            self.loop_memory.record_loop_end(self.game_state)

        self.game_state = GameState.from_world_data(
            self.data_dir / "scenarios" / "world.yaml",
            self.data_dir / "scenarios" / "npcs.yaml",
        )
        self.game_state.loop_count = self.loop_memory.total_loops + 1
        cap = self.cfg_sanity_cap
        base = self.cfg_starting_sanity
        self.game_state.sanity = min(cap, base - max(0, self.loop_memory.total_loops * 5))
        self.game_state.discovered_facts = list(self.loop_memory.discovered_facts)

        for npc_id, npc in self.game_state.characters.items():
            prev_max = self.loop_memory.npc_max_trust.get(npc_id, 0)
            if prev_max > 0:
                npc.trust = int(prev_max * 0.3)

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

        lang = self.lang
        state_logs = self.game_state.apply_state_updates(event.effects)
        sanity_delta = event.sanity_impact
        self.game_state.modify_sanity(sanity_delta)
        self.game_state.advance_time(self.cfg_time_per_turn)

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

    def process_turn(self, player_input: str, choice_sanity_cost: int = 0, choice_id: str = "") -> TurnResult:
        if not self.game_state:
            return TurnResult(error="No active game. Call new_game() first.")

        if choice_sanity_cost:
            self.game_state.modify_sanity(choice_sanity_cost)

        if self.event_system and choice_id:
            self.event_system.last_choice_id = choice_id

        self.game_state.turn += 1

        if self.game_state.is_midnight:
            return self._handle_midnight()

        # --- Check scripted events first ---
        if self.event_system:
            event = self.event_system.check_events(
                self.game_state, self.loop_memory, player_input
            )
            if event:
                self.event_system.last_choice_id = ""
                return self._apply_event(event)
            self.event_system.last_choice_id = ""

        # --- Auto trust: interacting with NPCs at your location ---
        self._auto_trust_gain(player_input)

        # --- LLM generation for non-event turns ---
        system_prompt = self.prompt_builder.build_system_prompt(
            self.game_state, self.loop_memory, lang=self.lang,
        )
        if self.event_system:
            narrative_hints = self.event_system.get_narrative_hints(
                self.game_state, self.loop_memory, lang=self.lang,
            )
            if narrative_hints:
                system_prompt += "\n\n" + narrative_hints
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
        self._infer_location_from_input(player_input, parsed)
        self._log_turn(player_input, parsed)

        if self.event_system and parsed.entities:
            entity_text = " ".join(str(v) for v in parsed.entities.values() if v)
            combined_input = f"{player_input} {entity_text}"
            late_event = self.event_system.check_events(
                self.game_state, self.loop_memory, combined_input
            )
            if late_event:
                event_result = self._apply_event(late_event)
                event_result.consistency_log = "\n".join(consistency_log_parts)
                return event_result

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

    # keyword → location_id mapping (order matters: more specific first)
    _LOCATION_KEYWORDS: list[tuple[str, list[str]]] = [
        ("lighthouse", ["lighthouse", "灯塔"]),
        ("library",    ["library", "图书馆", "书馆"]),
        ("church",     ["church", "教堂", "圣安德鲁", "st. andrew"]),
        ("docks",      ["dock", "docks", "pier", "码头", "栈桥", "渔港"]),
        ("caves",      ["cave", "caves", "洞穴", "山洞", "洞口"]),
        ("inn",        ["inn", "旅馆", "旅店", "hotel"]),
    ]

    def _infer_location_from_input(
        self, player_input: str, parsed: "ParsedOutput"
    ) -> bool:
        """Fallback: if the LLM forgot move_player, infer location from input + entities.

        Runs after _apply_parsed_output. Returns True if location was changed.
        """
        if not self.game_state:
            return False
        if any(u.get("type") == "move_player" for u in parsed.state_updates):
            return False  # LLM already handled it

        entity_loc = (parsed.entities or {}).get("location", "")
        combined = f"{player_input} {entity_loc}".lower()

        for loc_id, keywords in self._LOCATION_KEYWORDS:
            if loc_id == self.game_state.location:
                continue
            if any(kw in combined for kw in keywords):
                logger.info(
                    "Auto-inferred move_player to %s (LLM omitted it)", loc_id
                )
                self.game_state.move_player(loc_id)
                return True
        return False

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
        base = (
            "The church bells begin to toll. One. Two. Three... The sound "
            "reverberates through your skull, each strike erasing the world a "
            "little more. The streets dissolve. The buildings fold inward. "
            "Midnight. The loop closes. And then -- dusk. The salt wind. "
            "The letter in your pocket. Again."
        ) if self.lang != "zh" else (
            "教堂钟声响起。一下。两下。三下……声波穿透你的头骨，每一击都在抹去"
            "更多的世界。街道溶解。建筑向内折叠。午夜。循环闭合。然后——黄昏。"
            "咸涩的海风。口袋里的信。又一次。"
        )
        hints = self._build_loop_hints()
        narration = f"{base}\n\n{hints}" if hints else base
        return TurnResult(
            narration=narration,
            choices=[],
            is_ending=False,
        )

    ALL_EXPLORABLE_LOCATIONS = ["inn", "library", "church", "docks"]

    def _build_loop_hints(self) -> str:
        if not self.game_state:
            return ""
        gs = self.game_state
        lang = self.lang
        hints: list[str] = []

        visited = gs.flags.get("_visited_locations", [])
        if not isinstance(visited, list):
            visited = []

        loc_names_map = {
            "library": ("图书馆", "the Library"),
            "church": ("教堂", "the Church"),
            "docks": ("码头", "the Docks"),
            "lighthouse": ("灯塔", "the Lighthouse"),
        }
        for loc_id in self.ALL_EXPLORABLE_LOCATIONS:
            if loc_id != "inn" and loc_id not in visited:
                zh, en = loc_names_map.get(loc_id, (loc_id, loc_id))
                if lang == "zh":
                    hints.append(f"你还未去过{zh}，那里可能藏有线索")
                else:
                    hints.append(f"You haven't visited {en} yet -- there may be clues there")

        for npc_id, npc in gs.characters.items():
            if not npc.alive:
                continue
            if self.event_system:
                for event in self.event_system.events:
                    if event.id in self.event_system.fired_events:
                        continue
                    trust_req = event.trigger.get("npc_trust", {}).get(npc_id)
                    if trust_req and 0 < trust_req - npc.trust <= 15:
                        if lang == "zh":
                            hints.append(f"{npc.name}似乎还有话没说完（信任: {npc.trust}/{trust_req}）")
                        else:
                            hints.append(f"{npc.name} seems to have more to say (trust: {npc.trust}/{trust_req})")
                        break

        if not hints:
            return ""

        new_facts = len([f for f in gs.discovered_facts
                         if f not in self.loop_memory.discovered_facts])
        npcs_met = sum(1 for n in gs.characters.values() if n.met and n.alive)

        if lang == "zh":
            header = "─── 你的调查笔记 ───"
            summary = f"本轮你发现了 {new_facts} 条新线索，与 {npcs_met} 位NPC交谈。"
            next_label = "下一轮建议："
        else:
            header = "--- Your Investigation Notes ---"
            summary = f"This loop you found {new_facts} new clue(s) and spoke with {npcs_met} NPC(s)."
            next_label = "Next loop suggestions:"

        bullet = "\n".join(f"  \u25b8 {h}" for h in hints[:4])
        return f"{header}\n{summary}\n\n{next_label}\n{bullet}"

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
            and "elias_found_alternative_method" in state.discovered_facts
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
        return self.event_system.format_timeline_html(self.game_state, lang=self.lang)
