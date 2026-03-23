"""Run all ablation variants and produce a comparison table.

Usage:
    python -m eval.ablation_runner

Produces eval/results/ablation_comparison.md with a single table comparing
baseline vs each ablation variant.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from eval.scenarios import SCENARIOS
from eval.metrics import TurnRecord, compute_metrics
from eval.run_eval import run_single_scenario
from src.game.engine import GameEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ABLATIONS = [
    {"name": "baseline", "setup": lambda e: None},
    {"name": "no_consistency", "setup": lambda e: setattr(e.hard_checker, 'check', lambda *a, **kw: [])},
    {
        "name": "no_knowledge",
        "setup": lambda e: setattr(
            e, '_processors',
            [p for p in e._processors if "Knowledge" not in type(p).__name__]
        ),
    },
]


def run_ablation_suite():
    results_by_variant: dict[str, dict] = {}

    for ablation in ABLATIONS:
        name = ablation["name"]
        logger.info("=" * 40 + f" {name} " + "=" * 40)

        engine = GameEngine()
        ablation["setup"](engine)

        all_records: list[TurnRecord] = []
        for scenario in SCENARIOS:
            if scenario.get("loops", 1) > 1 and name == "no_knowledge":
                continue
            try:
                records = run_single_scenario(scenario, engine)
                all_records.extend(records)
            except Exception as e:
                logger.error("Scenario %s failed under %s: %s", scenario["id"], name, e)

        result = compute_metrics(all_records)
        results_by_variant[name] = {
            "turns": result.total_turns,
            "violation_rate": result.violation_rate,
            "intent_accuracy": result.intent_accuracy,
            "latency_p50": result.latency_p50_ms,
            "latency_p95": result.latency_p95_ms,
            "knowledge_recall": result.knowledge_recall,
            "avg_narration_len": result.avg_narration_length,
            "dialogue_rate": result.dialogue_presence_rate,
        }

    table = _format_comparison_table(results_by_variant)

    out_dir = Path("eval/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"ablation_comparison_{ts}.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(table)
    logger.info("Saved ablation comparison to %s", path)
    print(table)


def _format_comparison_table(data: dict[str, dict]) -> str:
    lines = [
        "## Table 4: Ablation Study Results",
        "",
        "| Metric | Baseline | No Consistency | No Knowledge |",
        "|--------|----------|----------------|--------------|",
    ]

    metrics = [
        ("Turns evaluated", "turns", "{:.0f}"),
        ("**Violation rate**", "violation_rate", "**{:.2%}**"),
        ("**Intent accuracy**", "intent_accuracy", "**{:.2%}**"),
        ("Latency P50 (ms)", "latency_p50", "{:.0f}"),
        ("Latency P95 (ms)", "latency_p95", "{:.0f}"),
        ("Knowledge recall", "knowledge_recall", "{:.2%}"),
        ("Avg narration length", "avg_narration_len", "{:.0f}"),
        ("Dialogue presence", "dialogue_rate", "{:.2%}"),
    ]

    variants = ["baseline", "no_consistency", "no_knowledge"]
    for label, key, fmt in metrics:
        cells = []
        for v in variants:
            val = data.get(v, {}).get(key, 0)
            cells.append(fmt.format(val))
        lines.append(f"| {label} | {' | '.join(cells)} |")

    lines.extend([
        "",
        "*Ablation `no_consistency` disables HardRulesChecker; "
        "`no_knowledge` removes KnowledgePre/PostProcessors from the pipeline.*",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    run_ablation_suite()
