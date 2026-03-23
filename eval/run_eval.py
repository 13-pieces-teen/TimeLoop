"""Automated evaluation harness for TimeLoop.

Usage:
    python -m eval.run_eval                    # run all scenarios
    python -m eval.run_eval --scenario S1      # run one scenario
    python -m eval.run_eval --ablation no_consistency  # ablation study

Outputs:
    eval/results/eval_YYYYMMDD_HHMMSS.jsonl    — per-turn records
    eval/results/report_YYYYMMDD_HHMMSS.md     — formatted tables
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime
from pathlib import Path

from eval.scenarios import SCENARIOS
from eval.metrics import TurnRecord, compute_metrics, format_results_table, format_branching_table
from src.game.engine import GameEngine, TurnResult

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_single_scenario(
    scenario: dict,
    engine: GameEngine,
    ablation: str = "",
) -> list[TurnRecord]:
    """Execute one scenario and collect turn records."""
    records: list[TurnRecord] = []
    lang = scenario.get("lang", "en")
    engine.lang = lang
    sid = scenario["id"]

    logger.info("Running scenario: %s — %s", sid, scenario["description"])

    result = engine.new_game()
    _log_event_result(records, sid, 0, result, "[NEW_GAME]")

    steps = scenario.get("steps", [])
    if scenario.get("loops", 1) >= 2:
        steps = scenario.get("loop1_steps", steps)

    for i, step in enumerate(steps, start=1):
        record = TurnRecord(scenario_id=sid, turn=i)

        player_input = step.get("input", "")
        choice_id = step.get("choice_id", "")
        record.intent_expected = step.get("expect_intent", "")
        record.knowledge_expected = step.get("expect_knowledge", "")

        t0 = time.perf_counter()

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

        record.player_input = player_input
        record.intent_predicted = result.intent
        record.narration = result.narration or ""
        record.has_dialogue = bool(result.dialogue_speaker and result.dialogue_text)
        record.latency_ms = elapsed_ms
        record.sanity = engine.game_state.sanity if engine.game_state else 0
        record.location = engine.game_state.location if engine.game_state else ""
        record.facts_count = len(engine.game_state.discovered_facts) if engine.game_state else 0

        if engine.game_state:
            record.trust_snapshot = {
                nid: npc.trust for nid, npc in engine.game_state.characters.items()
            }

        if result.consistency_log and result.consistency_log != "(clean)":
            record.consistency_violations = [result.consistency_log]

        if result.knowledge_used:
            record.knowledge_detected = [k["knowledge_id"] for k in result.knowledge_used]

        records.append(record)

        if result.is_loop_reset:
            break
        if result.is_ending:
            break

    if scenario.get("loops", 1) >= 2 and "loop2_steps" in scenario:
        loop_result = engine.new_loop()
        _log_event_result(records, sid, len(records), loop_result, "[NEW_LOOP]")

        for i, step in enumerate(scenario["loop2_steps"], start=len(records) + 1):
            record = TurnRecord(scenario_id=sid, turn=i)
            player_input = step.get("input", "")
            record.intent_expected = step.get("expect_intent", "")
            record.knowledge_expected = step.get("expect_knowledge", "")

            t0 = time.perf_counter()
            result = engine.process_turn(player_input)
            elapsed_ms = (time.perf_counter() - t0) * 1000

            record.player_input = player_input
            record.intent_predicted = result.intent
            record.narration = result.narration or ""
            record.has_dialogue = bool(result.dialogue_speaker and result.dialogue_text)
            record.latency_ms = elapsed_ms
            record.sanity = engine.game_state.sanity if engine.game_state else 0
            record.location = engine.game_state.location if engine.game_state else ""

            if result.knowledge_used:
                record.knowledge_detected = [k["knowledge_id"] for k in result.knowledge_used]

            records.append(record)

    return records


def _log_event_result(records, sid, turn, result, label):
    records.append(TurnRecord(
        scenario_id=sid,
        turn=turn,
        player_input=label,
        intent_predicted=result.intent,
        narration=result.narration[:200] if result.narration else "",
        has_dialogue=bool(result.dialogue_speaker),
    ))


def run_branching_comparison(engine: GameEngine) -> list[dict]:
    """Run S2_branch_A and S2_branch_B and compare final states."""
    pairs = []
    scenarios_a = [s for s in SCENARIOS if s["id"] == "S2_branch_A"]
    scenarios_b = [s for s in SCENARIOS if s["id"] == "S2_branch_B"]
    if not scenarios_a or not scenarios_b:
        return pairs

    engine.lang = "en"
    records_a = run_single_scenario(scenarios_a[0], engine)
    state_a = engine.get_state_summary()

    records_b = run_single_scenario(scenarios_b[0], engine)
    state_b = engine.get_state_summary()

    gs_a = state_a.get("game_state", {})
    gs_b = state_b.get("game_state", {})

    trust_a = {k: v.get("trust", 0) for k, v in gs_a.get("characters", {}).items()}
    trust_b = {k: v.get("trust", 0) for k, v in gs_b.get("characters", {}).items()}
    trust_deltas = {k: trust_a.get(k, 0) - trust_b.get(k, 0) for k in set(trust_a) | set(trust_b)}

    facts_a = set(gs_a.get("discovered_facts", []))
    facts_b = set(gs_b.get("discovered_facts", []))

    pairs.append({
        "pair": "S2_A vs S2_B",
        "diverge_turn": 2,
        "trust_delta": str(trust_deltas),
        "facts_delta": f"+{len(facts_a - facts_b)} / -{len(facts_b - facts_a)}",
        "location_delta": f"{gs_a.get('location', '?')} vs {gs_b.get('location', '?')}",
        "narration_sim": "N/A (manual)",
    })
    return pairs


def save_results(records: list[TurnRecord], result, branch_pairs, ablation: str = ""):
    out_dir = Path("eval/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{ablation}" if ablation else ""

    jsonl_path = out_dir / f"eval_{ts}{suffix}.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r.__dict__, ensure_ascii=False, default=str) + "\n")
    logger.info("Saved %d turn records to %s", len(records), jsonl_path)

    model_name = "Qwen2.5-7B" + (f" ({ablation})" if ablation else "")
    report = format_results_table(result, model_name)
    if branch_pairs:
        report += "\n\n" + format_branching_table(branch_pairs)

    md_path = out_dir / f"report_{ts}{suffix}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info("Saved report to %s", md_path)


def main():
    parser = argparse.ArgumentParser(description="TimeLoop Evaluation Harness")
    parser.add_argument("--scenario", type=str, default="", help="Run specific scenario ID")
    parser.add_argument(
        "--ablation", type=str, default="",
        choices=["", "no_consistency", "no_knowledge", "simple_prompt"],
        help="Ablation study variant",
    )
    args = parser.parse_args()

    engine = GameEngine()

    if args.ablation == "no_consistency":
        logger.info("ABLATION: Disabling hard rules checker")
        engine.hard_checker.check = lambda *a, **kw: []
    elif args.ablation == "no_knowledge":
        logger.info("ABLATION: Disabling knowledge processors")
        engine._processors = [
            p for p in engine._processors
            if "Knowledge" not in type(p).__name__
        ]

    scenarios = SCENARIOS
    if args.scenario:
        scenarios = [s for s in SCENARIOS if args.scenario in s["id"]]
        if not scenarios:
            logger.error("No scenario matching '%s'", args.scenario)
            return

    all_records: list[TurnRecord] = []
    for scenario in scenarios:
        try:
            records = run_single_scenario(scenario, engine)
            all_records.extend(records)
        except Exception as e:
            logger.error("Scenario %s failed: %s", scenario["id"], e)

    branch_pairs = run_branching_comparison(engine)

    result = compute_metrics(all_records)
    save_results(all_records, result, branch_pairs, args.ablation)

    print("\n" + "=" * 60)
    print(format_results_table(result))
    if branch_pairs:
        print()
        print(format_branching_table(branch_pairs))
    print("=" * 60)


if __name__ == "__main__":
    main()
