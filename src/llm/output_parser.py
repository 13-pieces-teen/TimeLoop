from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

REQUIRED_KEYS = {
    "intent",
    "narration",
    "choices",
    "state_updates",
    "sanity_impact",
}


@dataclass
class ParsedOutput:
    intent: str = "UNKNOWN"
    entities: dict[str, str] = field(default_factory=dict)
    narration: str = ""
    dialogue: dict[str, str | None] = field(default_factory=dict)
    choices: list[dict[str, Any]] = field(default_factory=list)
    state_updates: list[dict[str, Any]] = field(default_factory=list)
    sanity_impact: int = 0
    time_advance: int = 30
    raw: dict = field(default_factory=dict)
    parse_errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return bool(self.narration) and len(self.choices) > 0 and not self.parse_errors


def _try_repair_truncated_json(text: str) -> dict | None:
    """Attempt to repair JSON truncated by max_tokens."""
    open_braces = text.count("{") - text.count("}")
    open_brackets = text.count("[") - text.count("]")
    if open_braces <= 0 and open_brackets <= 0:
        return None

    repaired = text.rstrip()
    if repaired and repaired[-1] not in '",}]':
        last_quote = repaired.rfind('"')
        last_comma = repaired.rfind(",")
        last_colon = repaired.rfind(":")
        cut = max(last_quote, last_comma, last_colon)
        if cut > 0:
            repaired = repaired[:cut]
            if repaired.endswith(",") or repaired.endswith(":"):
                repaired = repaired[:-1]

    repaired += "]" * max(0, open_brackets)
    repaired += "}" * max(0, open_braces)

    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    narration_match = re.search(r'"narration"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    if narration_match:
        return {"narration": narration_match.group(1), "_repaired": True}
    return None


def extract_json(text: str) -> dict | None:
    """Try to extract a JSON object from potentially messy LLM output."""
    text = text.strip()
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start : brace_end + 1])
        except json.JSONDecodeError:
            pass

    repaired = _try_repair_truncated_json(text)
    if repaired:
        logger.warning("Repaired truncated JSON from LLM output")
        return repaired

    return None


def _extract_narration_from_raw(raw_text: str) -> str:
    """Last-resort: pull the narration value from raw text even if JSON is broken."""
    m = re.search(r'"narration"\s*:\s*"((?:[^"\\]|\\.)*)"', raw_text)
    if m and len(m.group(1)) > 20:
        return m.group(1)
    return ""


def parse_llm_output(raw_text: str) -> ParsedOutput:
    data = extract_json(raw_text)
    if data is None:
        salvaged = _extract_narration_from_raw(raw_text)
        narration = salvaged if salvaged else (
            "The world flickers, as if reality itself lost its thread for a moment. "
            "You steady yourself and try again."
        )
        return ParsedOutput(
            narration=narration,
            parse_errors=["Failed to parse JSON from LLM response"],
            choices=[
                {"id": "retry", "text": "Try again", "sanity_cost": 0},
                {"id": "wait", "text": "Wait and observe", "sanity_cost": 0},
                {"id": "leave", "text": "Leave this place", "sanity_cost": 0},
            ],
        )

    errors = []
    for key in REQUIRED_KEYS:
        if key not in data:
            errors.append(f"Missing key: {key}")

    choices = data.get("choices", [])
    if not isinstance(choices, list) or len(choices) == 0:
        choices = [
            {"id": "continue", "text": "Continue", "sanity_cost": 0},
            {"id": "wait", "text": "Wait and observe", "sanity_cost": 0},
            {"id": "leave", "text": "Leave", "sanity_cost": 0},
        ]
        errors.append("Invalid or missing choices, using fallback")

    dialogue = data.get("dialogue", {})
    if dialogue is None:
        dialogue = {"speaker": None, "text": None}

    return ParsedOutput(
        intent=data.get("intent", "UNKNOWN"),
        entities=data.get("entities", {}),
        narration=data.get("narration", ""),
        dialogue=dialogue,
        choices=choices,
        state_updates=data.get("state_updates", []),
        sanity_impact=int(data.get("sanity_impact", 0)),
        time_advance=int(data.get("time_advance", 30)),
        raw=data,
        parse_errors=errors,
    )
