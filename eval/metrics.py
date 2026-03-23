"""Quantitative evaluation metrics for the TimeLoop NLP system.

Reads trajectory logs produced by the game engine or by `run_eval.py`
and computes the following metrics:

1. Consistency violation rate (hard-rule violations / total turns)
2. Intent accuracy (predicted intent vs expected intent)
3. Response latency (P50, P95, mean)
4. Branching divergence (state difference after divergent choices)
5. Knowledge detection recall (cross-loop knowledge correctly detected)
6. NLG quality proxy — average narration length, dialogue presence rate
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TurnRecord:
    scenario_id: str = ""
    turn: int = 0
    player_input: str = ""
    intent_expected: str = ""
    intent_predicted: str = ""
    narration: str = ""
    has_dialogue: bool = False
    consistency_violations: list[str] = field(default_factory=list)
    knowledge_expected: str = ""
    knowledge_detected: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    sanity: int = 100
    location: str = ""
    trust_snapshot: dict[str, int] = field(default_factory=dict)
    facts_count: int = 0


@dataclass
class EvalResult:
    total_turns: int = 0
    total_scenarios: int = 0

    # Consistency
    total_violations: int = 0
    critical_violations: int = 0
    violation_rate: float = 0.0
    violations_by_rule: dict[str, int] = field(default_factory=dict)

    # Intent accuracy
    intent_total: int = 0
    intent_correct: int = 0
    intent_accuracy: float = 0.0

    # Latency
    latency_mean_ms: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_max_ms: float = 0.0

    # Knowledge
    knowledge_total: int = 0
    knowledge_detected: int = 0
    knowledge_recall: float = 0.0

    # NLG quality proxies
    avg_narration_length: float = 0.0
    dialogue_presence_rate: float = 0.0

    # Branching
    branch_pairs: list[dict] = field(default_factory=list)


def compute_metrics(records: list[TurnRecord]) -> EvalResult:
    """Compute all metrics from a list of turn records."""
    if not records:
        return EvalResult()

    result = EvalResult(
        total_turns=len(records),
        total_scenarios=len(set(r.scenario_id for r in records)),
    )

    latencies = []
    narration_lengths = []
    dialogue_count = 0

    for r in records:
        # Consistency
        for v in r.consistency_violations:
            result.total_violations += 1
            rule_id = v if isinstance(v, str) else v.get("rule_id", "unknown")
            result.violations_by_rule[rule_id] = result.violations_by_rule.get(rule_id, 0) + 1

        # Intent
        if r.intent_expected:
            result.intent_total += 1
            if r.intent_predicted.upper() == r.intent_expected.upper():
                result.intent_correct += 1

        # Latency
        if r.latency_ms > 0:
            latencies.append(r.latency_ms)

        # Knowledge
        if r.knowledge_expected:
            result.knowledge_total += 1
            if r.knowledge_expected in r.knowledge_detected:
                result.knowledge_detected_count = getattr(result, 'knowledge_detected_count', 0) + 1

        # NLG
        narration_lengths.append(len(r.narration))
        if r.has_dialogue:
            dialogue_count += 1

    result.violation_rate = result.total_violations / max(1, result.total_turns)

    if result.intent_total > 0:
        result.intent_accuracy = result.intent_correct / result.intent_total

    if latencies:
        latencies.sort()
        result.latency_mean_ms = statistics.mean(latencies)
        result.latency_p50_ms = latencies[len(latencies) // 2]
        result.latency_p95_ms = latencies[int(len(latencies) * 0.95)]
        result.latency_max_ms = max(latencies)

    if result.knowledge_total > 0:
        result.knowledge_recall = getattr(result, 'knowledge_detected_count', 0) / result.knowledge_total

    if narration_lengths:
        result.avg_narration_length = statistics.mean(narration_lengths)
    result.dialogue_presence_rate = dialogue_count / max(1, result.total_turns)

    return result


def format_results_table(result: EvalResult, model_name: str = "Qwen2.5-7B") -> str:
    """Format results as a Markdown table suitable for report inclusion."""
    lines = [
        f"## Evaluation Results — {model_name}",
        "",
        "### Table 1: Core NLP Metrics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total turns evaluated | {result.total_turns} |",
        f"| Scenarios | {result.total_scenarios} |",
        f"| **Consistency violation rate** | **{result.violation_rate:.2%}** |",
        f"| Critical violations | {result.critical_violations} |",
        f"| **Intent accuracy** | **{result.intent_accuracy:.2%}** ({result.intent_correct}/{result.intent_total}) |",
        f"| **Response latency (P50)** | **{result.latency_p50_ms:.0f} ms** |",
        f"| Response latency (P95) | {result.latency_p95_ms:.0f} ms |",
        f"| Response latency (mean) | {result.latency_mean_ms:.0f} ms |",
        f"| Knowledge detection recall | {result.knowledge_recall:.2%} |",
        f"| Avg narration length (chars) | {result.avg_narration_length:.0f} |",
        f"| Dialogue presence rate | {result.dialogue_presence_rate:.2%} |",
        "",
        "### Table 2: Consistency Violations by Rule",
        "",
        "| Rule ID | Count | % of Total |",
        "|---------|-------|------------|",
    ]
    for rule_id, count in sorted(result.violations_by_rule.items(), key=lambda x: -x[1]):
        pct = count / max(1, result.total_turns)
        lines.append(f"| {rule_id} | {count} | {pct:.1%} |")
    if not result.violations_by_rule:
        lines.append("| (none) | 0 | 0% |")

    return "\n".join(lines)


def format_branching_table(pairs: list[dict]) -> str:
    """Format branching divergence analysis."""
    lines = [
        "### Table 3: Branching Divergence Analysis",
        "",
        "| Scenario Pair | Diverge Point | Trust Δ | Facts Δ | Location Δ | Narration Similarity |",
        "|---------------|---------------|---------|---------|------------|---------------------|",
    ]
    for p in pairs:
        lines.append(
            f"| {p.get('pair', 'N/A')} | Turn {p.get('diverge_turn', '?')} "
            f"| {p.get('trust_delta', 'N/A')} | {p.get('facts_delta', 'N/A')} "
            f"| {p.get('location_delta', 'N/A')} | {p.get('narration_sim', 'N/A')} |"
        )
    return "\n".join(lines)


def load_trajectory(path: str | Path) -> list[dict]:
    """Load a JSONL trajectory file."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
