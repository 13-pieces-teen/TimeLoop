from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.state.game_state import GameState
from src.state.loop_memory import LoopMemory
from src.state.sanity import SanitySystem


class PromptBuilder:
    """Assembles the multi-layer prompt for each game turn."""

    def __init__(self, config_dir: str | Path):
        config_dir = Path(config_dir)

        with open(config_dir / "prompts" / "system.txt", "r", encoding="utf-8") as f:
            self.system_base = f.read().strip()

        with open(
            config_dir / "prompts" / "npc_profiles.yaml", "r", encoding="utf-8"
        ) as f:
            self.npc_profiles = yaml.safe_load(f).get("profiles", {})

        self.sanity_system = SanitySystem(config_dir / "prompts" / "sanity_styles.yaml")

        with open(
            Path("data") / "scenarios" / "world.yaml", "r", encoding="utf-8"
        ) as f:
            self.world_data = yaml.safe_load(f)

        with open(
            Path("data") / "scenarios" / "npcs.yaml", "r", encoding="utf-8"
        ) as f:
            self.npcs_full_data = yaml.safe_load(f).get("npcs", {})

    def _get_npc_injection(self, game_state: GameState) -> str:
        """Build NPC profile injection for NPCs at the current location."""
        location = game_state.location
        injections = []
        for npc_id, npc in game_state.characters.items():
            if npc.location != location or not npc.alive:
                continue
            profile = self.npc_profiles.get(npc_id)
            if not profile:
                continue

            npc_full = self.npcs_full_data.get(npc_id, {})
            available_knowledge = self._get_available_knowledge(npc_full, npc.trust)

            text = profile["system_injection"]
            text = text.replace("{trust}", str(npc.trust))
            text = text.replace("{available_knowledge}", available_knowledge)
            injections.append(text)

        return "\n\n".join(injections)

    def _get_available_knowledge(self, npc_data: dict, trust: int) -> str:
        """Determine what knowledge an NPC can share at the given trust level."""
        knowledge = npc_data.get("knowledge", {})
        thresholds = npc_data.get("trust_thresholds", {})

        available = list(knowledge.get("public", []))

        threshold_map = {int(k): v for k, v in thresholds.items()}
        accessible_thresholds = sorted(
            t for t in threshold_map if t <= trust
        )
        behaviors = []
        for t in accessible_thresholds:
            behaviors.append(f"At trust {t}: {threshold_map[t]}")

        hidden = knowledge.get("hidden", [])
        if trust >= 50:
            available.extend(hidden[: (trust - 50) // 20 + 1])
        secret = knowledge.get("secret", [])
        if trust >= 90:
            available.extend(secret)

        lines = ["Known facts she/he can mention: " + "; ".join(available)]
        if behaviors:
            lines.append("Behavior at current trust: " + behaviors[-1])
        return "\n".join(lines)

    def _get_location_context(self, game_state: GameState) -> str:
        """Build location description with sanity-appropriate flavor."""
        loc_data = self.world_data.get("locations", {}).get(game_state.location, {})
        if not loc_data:
            return f"You are at: {game_state.location}"

        base_desc = loc_data.get("description", "")
        sanity_notes = loc_data.get("sanity_notes", {})

        level = game_state.sanity_level
        if level == "lucid":
            return f"CURRENT LOCATION: {loc_data.get('name', game_state.location)}\n{base_desc}"

        extra = sanity_notes.get(level, sanity_notes.get("uneasy", ""))
        return (
            f"CURRENT LOCATION: {loc_data.get('name', game_state.location)}\n"
            f"{base_desc}\n"
            f"[Sanity overlay: {extra}]"
        )

    def _get_consistency_constraints(self, game_state: GameState) -> str:
        facts = game_state.discovered_facts
        if not facts:
            return "No established facts yet."
        return "ESTABLISHED FACTS (must not contradict):\n" + "\n".join(
            f"- {f}" for f in facts
        )

    def _get_turn_history_summary(self, game_state: GameState) -> str:
        if not game_state.turn_history:
            return "No previous actions this loop."
        lines = []
        for i, turn in enumerate(game_state.turn_history):
            player_action = turn.get("player_input", "?")
            narration_snippet = turn.get("narration", "")[:100]
            lines.append(f"Turn {i + 1}: Player: \"{player_action}\" → {narration_snippet}...")
        return "RECENT HISTORY:\n" + "\n".join(lines)

    def build_system_prompt(
        self, game_state: GameState, loop_memory: LoopMemory
    ) -> str:
        parts = [
            self.system_base,
            "",
            "--- WORLD BACKGROUND FACTS (always true, NEVER contradict) ---",
            "- Thomas Holloway (Martha's husband) has been MISSING for 6 months. He is NOT present.",
            "- Dr. Elias Webb has been missing for 3 weeks. He is NOT present in town.",
            "- The town is unusually quiet. Most residents avoid going out after dark.",
            "- It is 1927 in Ravenhollow, a remote New England coastal town.",
            "- The player is a folklore lecturer from Boston University.",
            "",
            "--- SANITY STYLE ---",
            self.sanity_system.get_directive(game_state.sanity),
            "",
            "--- LOCATION ---",
            self._get_location_context(game_state),
            "",
            "--- NPC PROFILES ---",
            self._get_npc_injection(game_state) or "(No NPCs at this location)",
            "",
            "--- WORLD STATE ---",
            game_state.to_prompt_summary(),
            "",
            "--- LOOP MEMORY ---",
            loop_memory.to_prompt_summary(),
            "",
            "--- CONSISTENCY CONSTRAINTS ---",
            self._get_consistency_constraints(game_state),
            "",
            "--- TURN HISTORY ---",
            self._get_turn_history_summary(game_state),
        ]
        return "\n".join(parts)

    def build_user_message(self, player_input: str) -> str:
        return f"Player action: {player_input}"

    def build_opening_prompt(
        self, game_state: GameState, loop_memory: LoopMemory
    ) -> tuple[str, str]:
        """Build the prompt for the very first turn of a loop."""
        system = self.build_system_prompt(game_state, loop_memory)

        if loop_memory.total_loops == 0:
            user_msg = (
                "The player has just arrived in Ravenhollow for the first time. "
                "Generate the opening narration: describe the arrival at the inn at dusk, "
                "the atmosphere of the town, and the first interaction with Martha. "
                "This is the beginning of the story."
            )
        else:
            user_msg = (
                f"The loop has reset. This is loop #{loop_memory.total_loops + 1}. "
                "The player wakes at the inn's doorstep at 8 PM, clutching Elias's letter. "
                "They have fragmented memories from previous loops. "
                "Generate the loop-restart narration with a sense of deja vu."
            )
        return system, user_msg
