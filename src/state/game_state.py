from __future__ import annotations

import copy
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass
class NPCState:
    name: str
    trust: int = 0
    met: bool = False
    alive: bool = True
    location: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "trust": self.trust,
            "met": self.met,
            "alive": self.alive,
            "location": self.location,
        }


@dataclass
class GameState:
    loop_count: int = 1
    turn: int = 0
    time_minutes: int = 0  # minutes since 8 PM (0 = 8:00 PM, 240 = midnight)
    location: str = "inn"
    sanity: int = 100
    characters: dict[str, NPCState] = field(default_factory=dict)
    inventory: list[str] = field(default_factory=list)
    discovered_facts: list[str] = field(default_factory=list)
    flags: dict[str, bool] = field(default_factory=dict)
    turn_history: list[dict] = field(default_factory=list)

    @classmethod
    def from_world_data(cls, world_path: str | Path, npcs_path: str | Path) -> GameState:
        world = _load_yaml(world_path)
        npcs_data = _load_yaml(npcs_path)

        characters = {}
        for npc_id, npc_info in npcs_data.get("npcs", {}).items():
            if npc_id == "elias":
                continue
            characters[npc_id] = NPCState(
                name=npc_info["name"],
                trust=0,
                met=False,
                alive=True,
                location=npc_info.get("location", ""),
            )

        starting_items = [
            item["id"] for item in world.get("starting_inventory", [])
        ]

        return cls(
            characters=characters,
            inventory=starting_items,
        )

    @property
    def current_time_str(self) -> str:
        total_minutes = self.time_minutes
        hour = 20 + total_minutes // 60  # starts at 8 PM = 20:00
        minute = total_minutes % 60
        if hour >= 24:
            hour -= 24
        period = "AM" if hour >= 12 and hour < 13 or hour < 12 else "PM"
        display_hour = hour if hour <= 12 else hour - 12
        if display_hour == 0:
            display_hour = 12
        return f"{display_hour}:{minute:02d} {period}"

    @property
    def is_midnight(self) -> bool:
        return self.time_minutes >= 240

    @property
    def minutes_until_midnight(self) -> int:
        return max(0, 240 - self.time_minutes)

    @property
    def sanity_level(self) -> str:
        if self.sanity >= 80:
            return "lucid"
        elif self.sanity >= 50:
            return "uneasy"
        elif self.sanity >= 20:
            return "distorted"
        else:
            return "madness"

    def advance_time(self, minutes: int = 30) -> None:
        self.time_minutes = min(240, self.time_minutes + minutes)

    def modify_sanity(self, delta: int) -> int:
        old = self.sanity
        self.sanity = max(0, min(100, self.sanity + delta))
        return self.sanity - old

    def add_fact(self, fact: str) -> bool:
        if fact not in self.discovered_facts:
            self.discovered_facts.append(fact)
            return True
        return False

    def set_flag(self, key: str, value: bool) -> None:
        self.flags[key] = value

    def has_item(self, item_id: str) -> bool:
        return item_id in self.inventory

    def add_item(self, item_id: str) -> bool:
        if item_id not in self.inventory:
            self.inventory.append(item_id)
            return True
        return False

    def remove_item(self, item_id: str) -> bool:
        if item_id in self.inventory:
            self.inventory.remove(item_id)
            return True
        return False

    def update_trust(self, npc_id: str, delta: int) -> None:
        if npc_id in self.characters:
            npc = self.characters[npc_id]
            npc.trust = max(0, min(100, npc.trust + delta))
            npc.met = True

    def move_player(self, location: str) -> None:
        self.location = location

    def add_turn_to_history(self, turn_data: dict) -> None:
        self.turn_history.append(turn_data)
        if len(self.turn_history) > 5:
            self.turn_history = self.turn_history[-5:]

    def apply_state_updates(self, updates: list[dict]) -> list[str]:
        """Apply a list of state updates from LLM output. Returns log messages."""
        logs = []
        for update in updates:
            utype = update.get("type", "")
            if utype == "add_fact":
                fact = update.get("fact", "")
                if fact and self.add_fact(fact):
                    logs.append(f"New fact discovered: {fact}")
            elif utype == "set_flag":
                key = update.get("key", "")
                value = update.get("value", True)
                if key:
                    self.set_flag(key, value)
                    logs.append(f"Flag set: {key}={value}")
            elif utype == "update_trust":
                npc = update.get("npc", "")
                delta = update.get("delta", 0)
                if npc and delta:
                    self.update_trust(npc, delta)
                    logs.append(f"Trust update: {npc} {delta:+d}")
            elif utype == "add_item":
                item = update.get("item", "")
                if item and self.add_item(item):
                    logs.append(f"Item acquired: {item}")
            elif utype == "remove_item":
                item = update.get("item", "")
                if item and self.remove_item(item):
                    logs.append(f"Item removed: {item}")
            elif utype == "move_player":
                loc = update.get("location", "")
                if loc:
                    self.move_player(loc)
                    logs.append(f"Moved to: {loc}")
        return logs

    def to_dict(self) -> dict:
        return {
            "loop_count": self.loop_count,
            "turn": self.turn,
            "time": self.current_time_str,
            "minutes_until_midnight": self.minutes_until_midnight,
            "location": self.location,
            "sanity": self.sanity,
            "sanity_level": self.sanity_level,
            "characters": {
                k: v.to_dict() for k, v in self.characters.items()
            },
            "inventory": self.inventory,
            "discovered_facts": self.discovered_facts,
            "flags": self.flags,
        }

    def to_prompt_summary(self) -> str:
        npcs_here = [
            f"{v.name} (trust: {v.trust})"
            for k, v in self.characters.items()
            if v.location == self.location and v.alive
        ]
        return (
            f"Location: {self.location} | Time: {self.current_time_str} "
            f"({self.minutes_until_midnight} min until midnight)\n"
            f"Sanity: {self.sanity}/100 ({self.sanity_level})\n"
            f"Inventory: {', '.join(self.inventory) or 'empty'}\n"
            f"NPCs here: {', '.join(npcs_here) or 'none'}\n"
            f"Known facts: {', '.join(self.discovered_facts[-10:]) or 'none'}\n"
            f"Flags: {json.dumps({k: v for k, v in self.flags.items() if v})}"
        )
