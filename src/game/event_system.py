from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from src.state.game_state import GameState
from src.state.loop_memory import LoopMemory

logger = logging.getLogger(__name__)


@dataclass
class Event:
    id: str
    act: int
    title: str
    title_zh: str
    trigger: dict[str, Any]
    narration: str
    effects: list[dict[str, Any]] = field(default_factory=list)
    choices: list[dict[str, Any]] = field(default_factory=list)
    dialogue: dict[str, str] | None = None
    sanity_impact: int = 0


@dataclass
class EventResult:
    event: Event
    triggered: bool = True


class EventSystem:
    """Pre-scripted event nodes that fire based on game state conditions."""

    def __init__(self, events_path: str | Path):
        with open(events_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.events: list[Event] = []
        for e in data.get("events", []):
            self.events.append(Event(
                id=e["id"],
                act=e.get("act", 0),
                title=e.get("title", e["id"]),
                title_zh=e.get("title_zh", e.get("title", e["id"])),
                trigger=e.get("trigger", {}),
                narration=e.get("narration", "").strip(),
                effects=e.get("effects", []),
                choices=e.get("choices", []),
                dialogue=e.get("dialogue"),
                sanity_impact=e.get("sanity_impact", 0),
            ))

        self.fired_events: set[str] = set()

    def reset_for_new_loop(self, loop_memory: LoopMemory) -> None:
        """Reset fired events for a new loop, keeping cross-loop unlocks."""
        self.fired_events = set()

    def check_events(
        self,
        game_state: GameState,
        loop_memory: LoopMemory,
        player_input: str = "",
    ) -> Event | None:
        """Check if any event should fire. Returns the highest-priority unfired event."""
        for event in self.events:
            if event.id in self.fired_events:
                continue
            if self._matches_trigger(event.trigger, game_state, loop_memory, player_input):
                self.fired_events.add(event.id)
                logger.info("Event triggered: %s (%s)", event.id, event.title)
                return event
        return None

    def _matches_trigger(
        self,
        trigger: dict[str, Any],
        gs: GameState,
        lm: LoopMemory,
        player_input: str,
    ) -> bool:
        if trigger.get("auto"):
            return True

        if "location" in trigger:
            if gs.location != trigger["location"]:
                return False

        if "min_turn" in trigger:
            if gs.turn < trigger["min_turn"]:
                return False

        if "flag" in trigger:
            if not gs.flags.get(trigger["flag"], False):
                return False

        if "not_flag" in trigger:
            if gs.flags.get(trigger["not_flag"], False):
                return False

        if "fact_required" in trigger:
            if trigger["fact_required"] not in gs.discovered_facts:
                return False

        if "npc_trust" in trigger:
            for npc_id, min_trust in trigger["npc_trust"].items():
                npc = gs.characters.get(npc_id)
                if not npc or npc.trust < min_trust:
                    return False

        if "max_minutes_remaining" in trigger:
            if gs.minutes_until_midnight > trigger["max_minutes_remaining"]:
                return False

        if "any_input_keyword" in trigger:
            if not player_input:
                return False
            keywords = trigger["any_input_keyword"]
            input_lower = player_input.lower()
            if not any(kw.lower() in input_lower for kw in keywords):
                return False

        return True

    def get_timeline(self, game_state: GameState) -> list[dict[str, Any]]:
        """Build visual timeline of all events and their status."""
        timeline = []
        for event in self.events:
            status = "completed" if event.id in self.fired_events else "locked"
            if status == "locked":
                if self._is_available_soon(event.trigger, game_state):
                    status = "available"

            timeline.append({
                "id": event.id,
                "act": event.act,
                "title": event.title,
                "title_zh": event.title_zh,
                "status": status,
            })
        return timeline

    def _is_available_soon(self, trigger: dict, gs: GameState) -> bool:
        """Check if an event's non-input conditions are close to being met."""
        if trigger.get("auto"):
            return True
        if "not_flag" in trigger and gs.flags.get(trigger["not_flag"], False):
            return False
        if "flag" in trigger and not gs.flags.get(trigger["flag"], False):
            return False
        if "location" in trigger and gs.location != trigger["location"]:
            return False
        return True

    def format_timeline(self, game_state: GameState) -> str:
        """Format the timeline for display in the UI."""
        timeline = self.get_timeline(game_state)
        current_act = 0
        lines = []

        for item in timeline:
            if item["act"] != current_act and item["act"] != 0:
                current_act = item["act"]
                lines.append(f"\n--- Act {current_act} ---")

            if item["status"] == "completed":
                icon = "[x]"
            elif item["status"] == "available":
                icon = "[>]"
            else:
                icon = "[ ]"

            lines.append(f"{icon} {item['title_zh']}")

        return "\n".join(lines)
