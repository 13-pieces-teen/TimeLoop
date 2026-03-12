from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from src.state.game_state import GameState

logger = logging.getLogger(__name__)


@dataclass
class Violation:
    rule_id: str
    description: str
    severity: str  # "critical" or "high"
    details: str


class HardRulesChecker:
    """Deterministic consistency checks on LLM output against game state."""

    def check(
        self,
        game_state: GameState,
        narration: str,
        dialogue: dict[str, Any],
        state_updates: list[dict[str, Any]],
    ) -> list[Violation]:
        violations = []
        violations.extend(self._check_dead_npc_dialogue(game_state, dialogue))
        violations.extend(self._check_npc_location(game_state, dialogue))
        violations.extend(self._check_item_existence(game_state, state_updates))
        violations.extend(self._check_locked_locations(game_state, state_updates))
        violations.extend(self._check_sanity_bounds(game_state, state_updates))
        return violations

    def _check_dead_npc_dialogue(
        self, state: GameState, dialogue: dict[str, Any]
    ) -> list[Violation]:
        speaker = dialogue.get("speaker")
        if not speaker:
            return []

        speaker_lower = speaker.lower()
        for npc_id, npc in state.characters.items():
            if npc_id == speaker_lower or npc.name.lower() == speaker_lower:
                if not npc.alive:
                    return [
                        Violation(
                            rule_id="dead_npcs_cannot_speak",
                            description="Dead NPC in dialogue",
                            severity="critical",
                            details=f"{npc.name} is dead but appears as dialogue speaker",
                        )
                    ]
        return []

    def _check_npc_location(
        self, state: GameState, dialogue: dict[str, Any]
    ) -> list[Violation]:
        speaker = dialogue.get("speaker")
        if not speaker:
            return []

        speaker_lower = speaker.lower()
        for npc_id, npc in state.characters.items():
            if npc_id == speaker_lower or npc.name.lower() == speaker_lower:
                if npc.location != state.location:
                    return [
                        Violation(
                            rule_id="npc_location_consistency",
                            description="NPC not at player location",
                            severity="critical",
                            details=(
                                f"{npc.name} is at {npc.location} but player is at "
                                f"{state.location}"
                            ),
                        )
                    ]
        return []

    def _check_item_existence(
        self, state: GameState, updates: list[dict[str, Any]]
    ) -> list[Violation]:
        violations = []
        for update in updates:
            if update.get("type") == "remove_item":
                item = update.get("item", "")
                if item and not state.has_item(item):
                    violations.append(
                        Violation(
                            rule_id="item_uniqueness",
                            description="Removing non-existent item",
                            severity="critical",
                            details=f"Tried to remove '{item}' but it's not in inventory",
                        )
                    )
        return violations

    def _check_locked_locations(
        self, state: GameState, updates: list[dict[str, Any]]
    ) -> list[Violation]:
        violations = []
        for update in updates:
            if update.get("type") == "move_player":
                loc = update.get("location", "")
                if loc in ("lighthouse", "caves"):
                    if loc == "lighthouse" and not state.flags.get(
                        "lighthouse_unlocked", False
                    ):
                        if not state.has_item("lighthouse_key"):
                            violations.append(
                                Violation(
                                    rule_id="locked_area_access",
                                    description="Accessing locked location",
                                    severity="critical",
                                    details=f"Lighthouse is locked and player has no key",
                                )
                            )
                    if loc == "caves" and not state.flags.get(
                        "caves_entrance_known", False
                    ):
                        if "caves_entrance_known" not in state.discovered_facts:
                            violations.append(
                                Violation(
                                    rule_id="locked_area_access",
                                    description="Accessing locked location",
                                    severity="critical",
                                    details="Caves entrance not yet discovered",
                                )
                            )
        return violations

    def _check_sanity_bounds(
        self, state: GameState, updates: list[dict[str, Any]]
    ) -> list[Violation]:
        return []

    def format_violations(self, violations: list[Violation]) -> str:
        if not violations:
            return ""
        lines = ["CONSISTENCY VIOLATIONS DETECTED:"]
        for v in violations:
            lines.append(f"  [{v.severity.upper()}] {v.rule_id}: {v.details}")
        return "\n".join(lines)
