"""Minimal ablation: with consistency vs without consistency.

Runs a small fixed scenario set and compares:
1) post-hoc hard-rule violation rate (final attempt per turn)
2) latency (mean / P50 / P95)
3) narrative usability proxies

Usage:
    python -m eval.min_ablation_consistency
"""

from __future__ import annotations

import json
import math
import statistics
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from eval.scenarios import SCENARIOS
from src.game.engine import GameEngine

SCENARIO_IDS = {
    "S1_linear_explore",
    "S3_knowledge_usage",
    "S4_consistency_stress",
    "S6_chinese",
}

FALLBACK_PREFIXES = (
    "The world flickers, as if reality itself lost its thread",
    "Something feels wrong. The world shimmers for a moment",
)


@dataclass
class TurnRow:
    variant: str
    scenario_id: str
    turn: int
    intent_expected: str
    intent_predicted: str
    latency_ms: float
    narration_len: int
    has_dialogue: bool
    is_fallback: bool
    final_violation_count: int


class ShadowHardChecker:
    """Collect real violations while optionally enforcing them in pipeline."""

    def __init__(self, real_checker, enforce: bool):
        self._real = real_checker
        self._enforce = enforce
        self._calls_current_turn: list[list] = []

    def start_turn(self) -> None:
        self._calls_current_turn = []

    def end_turn(self) -> list:
        if not self._calls_current_turn:
            return []
        return self._calls_current_turn[-1]

    def check(self, game_state, narration, dialogue, state_updates):
        violations = self._real.check(game_state, narration, dialogue, state_updates)
        self._calls_current_turn.append(violations)
        return violations if self._enforce else []

    def format_violations(self, violations):
        return self._real.format_violations(violations)


def _attach_shadow_checker(engine: GameEngine, enforce: bool) -> ShadowHardChecker:
    shadow = ShadowHardChecker(engine.hard_checker, enforce=enforce)
    engine.hard_checker = shadow
    for p in engine._processors:
        if type(p).__name__ == "LLMProcessor":
            p._hard_checker = shadow
    return shadow


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = max(0, min(len(sorted_vals) - 1, math.ceil(len(sorted_vals) * p) - 1))
    return sorted_vals[idx]


def _step_turn(engine: GameEngine, result, shadow: ShadowHardChecker, step: dict):
    player_input = step.get("input", "")
    choice_id = step.get("choice_id", "")
    t0 = time.perf_counter()
    shadow.start_turn()

    if choice_id:
        choices = result.choices or []
        matched = next((c for c in choices if c.get("id") == choice_id), None)
        if matched:
            player_input = matched.get("text", choice_id)
            san_cost = int(matched.get("sanity_cost", 0))
            trust_bonus = matched.get("trust_bonus", {})
            result = engine.process_turn(
                player_input,
                choice_sanity_cost=san_cost,
                choice_id=choice_id,
                trust_bonus=trust_bonus,
            )
        else:
            result = engine.process_turn(choice_id)
    else:
        result = engine.process_turn(player_input)

    elapsed_ms = (time.perf_counter() - t0) * 1000
    violations = shadow.end_turn()
    return result, elapsed_ms, violations


def run_variant(variant: str, enforce_consistency: bool) -> tuple[dict, list[TurnRow]]:
    engine = GameEngine()
    shadow = _attach_shadow_checker(engine, enforce=enforce_consistency)
    rows: list[TurnRow] = []

    selected = [s for s in SCENARIOS if s["id"] in SCENARIO_IDS]
    for scenario in selected:
        sid = scenario["id"]
        engine.lang = scenario.get("lang", "en")
        result = engine.new_game()

        steps = scenario.get("steps", [])
        if scenario.get("loops", 1) >= 2:
            steps = scenario.get("loop1_steps", steps)

        turn = 1
        for step in steps:
            result, elapsed_ms, violations = _step_turn(engine, result, shadow, step)
            narration = result.narration or ""
            rows.append(
                TurnRow(
                    variant=variant,
                    scenario_id=sid,
                    turn=turn,
                    intent_expected=step.get("expect_intent", ""),
                    intent_predicted=result.intent,
                    latency_ms=elapsed_ms,
                    narration_len=len(narration),
                    has_dialogue=bool(result.dialogue_speaker and result.dialogue_text),
                    is_fallback=any(narration.startswith(p) for p in FALLBACK_PREFIXES),
                    final_violation_count=len(violations),
                )
            )
            turn += 1
            if result.is_ending or result.is_loop_reset:
                break

        if scenario.get("loops", 1) >= 2 and "loop2_steps" in scenario:
            result = engine.new_loop()
            for step in scenario["loop2_steps"]:
                result, elapsed_ms, violations = _step_turn(engine, result, shadow, step)
                narration = result.narration or ""
                rows.append(
                    TurnRow(
                        variant=variant,
                        scenario_id=sid,
                        turn=turn,
                        intent_expected=step.get("expect_intent", ""),
                        intent_predicted=result.intent,
                        latency_ms=elapsed_ms,
                        narration_len=len(narration),
                        has_dialogue=bool(result.dialogue_speaker and result.dialogue_text),
                        is_fallback=any(narration.startswith(p) for p in FALLBACK_PREFIXES),
                        final_violation_count=len(violations),
                    )
                )
                turn += 1
                if result.is_ending or result.is_loop_reset:
                    break

    latencies = sorted([r.latency_ms for r in rows if r.latency_ms > 0])
    expected_rows = [r for r in rows if r.intent_expected]
    summary = {
        "variant": variant,
        "turns": len(rows),
        "violation_turns": sum(1 for r in rows if r.final_violation_count > 0),
        "violation_rate": (sum(1 for r in rows if r.final_violation_count > 0) / max(1, len(rows))),
        "latency_mean_ms": statistics.mean(latencies) if latencies else 0.0,
        "latency_p50_ms": _percentile(latencies, 0.50),
        "latency_p95_ms": _percentile(latencies, 0.95),
        "intent_acc": (
            sum(1 for r in expected_rows if r.intent_predicted.upper() == r.intent_expected.upper())
            / max(1, len(expected_rows))
        ),
        "avg_narr_len": statistics.mean([r.narration_len for r in rows]) if rows else 0.0,
        "dialogue_rate": (sum(1 for r in rows if r.has_dialogue) / max(1, len(rows))),
        "fallback_rate": (sum(1 for r in rows if r.is_fallback) / max(1, len(rows))),
        "usable_narration_rate": (
            sum(1 for r in rows if (r.narration_len >= 40 and not r.is_fallback)) / max(1, len(rows))
        ),
    }
    return summary, rows


def _format_markdown(baseline: dict, no_consistency: dict) -> str:
    lines = [
        "## Minimal Ablation: With vs Without Consistency",
        "",
        f"- Scenario set: {', '.join(sorted(SCENARIO_IDS))}",
        f"- Sample size: baseline n={baseline['turns']} turns; no_consistency n={no_consistency['turns']} turns",
        "",
        "| Metric | With Consistency | Without Consistency | Unit |",
        "|---|---:|---:|---|",
        f"| Post-hoc violation rate (final attempt) | {baseline['violation_rate']:.2%} | {no_consistency['violation_rate']:.2%} | % turns |",
        f"| Turns with >=1 violation | {baseline['violation_turns']} | {no_consistency['violation_turns']} | turns |",
        f"| Latency mean | {baseline['latency_mean_ms']:.0f} | {no_consistency['latency_mean_ms']:.0f} | ms |",
        f"| Latency P50 | {baseline['latency_p50_ms']:.0f} | {no_consistency['latency_p50_ms']:.0f} | ms |",
        f"| Latency P95 | {baseline['latency_p95_ms']:.0f} | {no_consistency['latency_p95_ms']:.0f} | ms |",
        f"| Intent accuracy | {baseline['intent_acc']:.2%} | {no_consistency['intent_acc']:.2%} | % |",
        f"| Avg narration length | {baseline['avg_narr_len']:.1f} | {no_consistency['avg_narr_len']:.1f} | chars |",
        f"| Dialogue presence rate | {baseline['dialogue_rate']:.2%} | {no_consistency['dialogue_rate']:.2%} | % turns |",
        f"| Fallback narration rate | {baseline['fallback_rate']:.2%} | {no_consistency['fallback_rate']:.2%} | % turns |",
        f"| Usable narration rate | {baseline['usable_narration_rate']:.2%} | {no_consistency['usable_narration_rate']:.2%} | % turns |",
        "",
        "> `without consistency` means the pipeline does not enforce hard-rule retry,",
        "> but violations are still measured post-hoc by a shadow checker on final attempt outputs.",
    ]
    return "\n".join(lines)


def main() -> None:
    load_dotenv()
    baseline, baseline_rows = run_variant("with_consistency", enforce_consistency=True)
    no_consistency, no_consistency_rows = run_variant("without_consistency", enforce_consistency=False)

    out_dir = Path("eval/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    md = _format_markdown(baseline, no_consistency)
    md_path = out_dir / f"min_ablation_consistency_{ts}.md"
    md_path.write_text(md, encoding="utf-8")

    raw = {
        "baseline": baseline,
        "no_consistency": no_consistency,
        "rows": [r.__dict__ for r in (baseline_rows + no_consistency_rows)],
    }
    raw_path = out_dir / f"min_ablation_consistency_{ts}.json"
    raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    print(md)
    print(f"\nSaved: {md_path}")
    print(f"Saved: {raw_path}")


if __name__ == "__main__":
    main()
