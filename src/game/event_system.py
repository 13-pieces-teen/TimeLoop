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
    narration_zh: str
    effects: list[dict[str, Any]] = field(default_factory=list)
    choices: list[dict[str, Any]] = field(default_factory=list)
    dialogue: dict[str, str] | None = None
    sanity_impact: int = 0

    def get_narration(self, lang: str = "en") -> str:
        return self.narration_zh if lang == "zh" else self.narration

    def get_title(self, lang: str = "en") -> str:
        return self.title_zh if lang == "zh" else self.title

    def get_dialogue(self, lang: str = "en") -> dict[str, str] | None:
        if not self.dialogue:
            return None
        if lang == "zh":
            return {
                "speaker": self.dialogue.get("speaker_zh", self.dialogue.get("speaker", "")),
                "text": self.dialogue.get("text_zh", self.dialogue.get("text", "")),
            }
        return {"speaker": self.dialogue.get("speaker", ""), "text": self.dialogue.get("text", "")}

    def get_choices(self, lang: str = "en") -> list[dict[str, Any]]:
        result = []
        for c in self.choices:
            entry = dict(c)
            if lang == "zh" and "text_zh" in c:
                entry["text"] = c["text_zh"]
            result.append(entry)
        return result


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
                narration_zh=e.get("narration_zh", e.get("narration", "")).strip(),
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

    def get_narrative_hints(self, game_state: GameState, loop_memory: LoopMemory, lang: str = "en") -> str:
        """Generate hints for the LLM about what the player should consider doing next."""
        hints = []
        for event in self.events:
            if event.id in self.fired_events or event.act == 0:
                continue
            trigger = event.trigger

            missing = []
            if "location" in trigger and game_state.location != trigger["location"]:
                loc = trigger["location"]
                missing.append(f"go to {loc}" if lang == "en" else f"前往{loc}")
            if "flag" in trigger and not game_state.flags.get(trigger["flag"], False):
                continue
            if "not_flag" in trigger and game_state.flags.get(trigger["not_flag"], False):
                continue
            if "fact_required" in trigger and trigger["fact_required"] not in game_state.discovered_facts:
                continue

            if "npc_trust" in trigger:
                trust_ok = True
                for npc_id, min_trust in trigger["npc_trust"].items():
                    npc = game_state.characters.get(npc_id)
                    if npc and npc.trust < min_trust:
                        gap = min_trust - npc.trust
                        if gap <= 20:
                            name = npc.name
                            missing.append(
                                f"build more trust with {name}"
                                if lang == "en"
                                else f"与{name}建立更多信任"
                            )
                        else:
                            trust_ok = False
                    elif not npc:
                        trust_ok = False
                if not trust_ok:
                    continue

            if not missing:
                title = event.get_title(lang)
                if "any_input_keyword" in trigger:
                    if lang == "zh":
                        hints.append(f"- 提示：可以探索与「{title}」相关的话题")
                    else:
                        hints.append(f"- Hint: explore topics related to \"{title}\"")
                else:
                    if lang == "zh":
                        hints.append(f"- 重要事件「{title}」即将触发")
                    else:
                        hints.append(f"- An important event \"{title}\" is close to triggering")
            elif len(missing) <= 2:
                title = event.get_title(lang)
                advice = "; ".join(missing)
                if lang == "zh":
                    hints.append(f"- 若想推进「{title}」，可以考虑{advice}")
                else:
                    hints.append(f"- To advance \"{title}\", consider: {advice}")

            if len(hints) >= 3:
                break

        if not hints:
            return ""
        header = "--- 叙事引导提示（自然融入叙述，不要直接告诉玩家）---" if lang == "zh" else \
            "--- NARRATIVE GUIDANCE (weave naturally into narration, do NOT tell the player directly) ---"
        return header + "\n" + "\n".join(hints)

    def format_timeline(self, game_state: GameState) -> str:
        """Format the timeline as plain text fallback."""
        timeline = self.get_timeline(game_state)
        current_act = 0
        lines = []
        for item in timeline:
            if item["act"] != current_act and item["act"] != 0:
                current_act = item["act"]
                lines.append(f"\n--- Act {current_act} ---")
            icon = {"completed": "[x]", "available": "[>]"}.get(item["status"], "[ ]")
            lines.append(f"{icon} {item['title_zh']}")
        return "\n".join(lines)

    def format_timeline_html(self, game_state: GameState, lang: str = "en") -> str:
        """Render the timeline as a horizontal flow with fog-of-war."""
        timeline = self.get_timeline(game_state)
        ACT_ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V"}

        acts: dict[int, list[dict]] = {}
        for item in timeline:
            acts.setdefault(item["act"], []).append(item)

        reached_act = 1
        for item in timeline:
            if item["status"] in ("completed", "available"):
                reached_act = max(reached_act, item["act"])

        html = ['<div class="tl-track">']

        sorted_acts = sorted(acts.keys())
        for act_idx, act_num in enumerate(sorted_acts):
            if act_num == 0:
                continue
            events = acts[act_num]
            is_revealed = act_num <= reached_act
            is_future = act_num > reached_act

            act_has_completed = any(e["status"] == "completed" for e in events)
            act_has_available = any(e["status"] == "available" for e in events)
            if act_has_completed:
                act_cls = "tl-act-done"
            elif act_has_available:
                act_cls = "tl-act-current"
            else:
                act_cls = "tl-act-locked"

            roman = ACT_ROMAN.get(act_num, str(act_num))
            html.append(
                f'<div class="tl-act-group">'
                f'<div class="tl-act-label {act_cls}">ACT {roman}</div>'
                f'<div class="tl-events">'
            )

            for i, ev in enumerate(events):
                status = ev["status"]
                main_title = ev["title_zh"] if lang == "zh" else ev["title"]
                sub_title = ev["title"] if lang == "zh" else ev["title_zh"]

                if is_future:
                    html.append(
                        '<div class="tl-node tl-fog">'
                        '<div class="tl-dot tl-dot-locked"></div>'
                        '<div class="tl-card tl-card-locked">'
                        '<div class="tl-lock">&#x1f512;</div>'
                        '</div>'
                        '</div>'
                    )
                elif status == "completed":
                    html.append(
                        f'<div class="tl-node">'
                        f'<div class="tl-dot tl-dot-done">'
                        f'<svg width="10" height="10" viewBox="0 0 10 10">'
                        f'<polyline points="2,5 4.5,7.5 8,2.5" fill="none" '
                        f'stroke="#0b0e17" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
                        f'</svg></div>'
                        f'<div class="tl-card tl-card-done">'
                        f'<div class="tl-title">{main_title}</div>'
                        f'<div class="tl-sub">{sub_title}</div>'
                        f'</div></div>'
                    )
                elif status == "available":
                    html.append(
                        f'<div class="tl-node">'
                        f'<div class="tl-dot tl-dot-active"></div>'
                        f'<div class="tl-card tl-card-active">'
                        f'<div class="tl-title">{main_title}</div>'
                        f'<div class="tl-sub">{sub_title}</div>'
                        f'</div></div>'
                    )
                else:
                    html.append(
                        f'<div class="tl-node">'
                        f'<div class="tl-dot tl-dot-pending"></div>'
                        f'<div class="tl-card tl-card-pending">'
                        f'<div class="tl-title">{main_title}</div>'
                        f'<div class="tl-sub">{sub_title}</div>'
                        f'</div></div>'
                    )

                if i < len(events) - 1:
                    line_cls = "tl-line-done" if status == "completed" else "tl-line-dim"
                    html.append(f'<div class="tl-line {line_cls}"></div>')

            html.append('</div></div>')

            if act_idx < len(sorted_acts) - 1:
                bridge_cls = "tl-bridge-done" if is_revealed and act_has_completed else "tl-bridge-dim"
                html.append(f'<div class="tl-bridge {bridge_cls}"></div>')

        html.append('</div>')
        return "".join(html)
