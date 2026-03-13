from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LoopMemory:
    total_loops: int = 0
    discovered_facts: list[str] = field(default_factory=list)
    unlocked_choices: list[str] = field(default_factory=list)
    endings_seen: list[str] = field(default_factory=list)
    npc_max_trust: dict[str, int] = field(default_factory=dict)
    last_loop_visited_locations: list[str] = field(default_factory=list)
    last_loop_new_facts: list[str] = field(default_factory=list)
    last_loop_npcs_talked: list[str] = field(default_factory=list)

    def record_loop_end(self, game_state) -> None:
        """Absorb relevant info from the ending game state before reset."""
        self.total_loops += 1

        old_facts = set(self.discovered_facts)
        self.last_loop_new_facts = []
        for fact in game_state.discovered_facts:
            if fact not in self.discovered_facts:
                self.discovered_facts.append(fact)
            if fact not in old_facts:
                self.last_loop_new_facts.append(fact)

        self.last_loop_npcs_talked = [
            npc_id for npc_id, npc in game_state.characters.items()
            if npc.met and npc.alive
        ]

        self.last_loop_visited_locations = list(
            game_state.flags.get("_visited_locations", [])
        ) if isinstance(game_state.flags.get("_visited_locations"), list) else []

        for npc_id, npc in game_state.characters.items():
            prev_max = self.npc_max_trust.get(npc_id, 0)
            self.npc_max_trust[npc_id] = max(prev_max, npc.trust)

    def record_ending(self, ending_id: str) -> None:
        if ending_id not in self.endings_seen:
            self.endings_seen.append(ending_id)

    def unlock_choice(self, choice_id: str) -> None:
        if choice_id not in self.unlocked_choices:
            self.unlocked_choices.append(choice_id)

    def to_dict(self) -> dict:
        return {
            "total_loops": self.total_loops,
            "discovered_facts": self.discovered_facts,
            "unlocked_choices": self.unlocked_choices,
            "endings_seen": self.endings_seen,
            "npc_max_trust": self.npc_max_trust,
        }

    def to_prompt_summary(self) -> str:
        if self.total_loops == 0:
            return "This is your first loop. You have no prior memories."

        lines = [
            f"This is loop #{self.total_loops + 1}.",
            f"From previous loops, you remember: {', '.join(self.discovered_facts) or 'nothing yet'}.",
        ]
        if self.unlocked_choices:
            lines.append(
                f"Unlocked options from past experience: {', '.join(self.unlocked_choices)}."
            )
        if self.endings_seen:
            lines.append(
                f"You have a vague sense of deja vu about: {', '.join(self.endings_seen)}."
            )
        return "\n".join(lines)
