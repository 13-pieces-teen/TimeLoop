# Report Blueprint — Soundness Sections

Below are draft outlines and key sentences for the report sections
that directly impact the **Soundness** rubric criterion. Copy, adapt,
and expand these into your final report.

---

## Section 3: Task & Data (≈0.7 pages)

### 3.1 Task Formulation

> We formulate player input understanding as **intent classification
> over K action types** (EXPLORE, ASK, NEGOTIATE, USE_ITEM, SPECIAL).
> Given the predicted intent and the current narrative state, we update
> a structured memory and generate the next plot segment under explicit
> **consistency constraints**.

**Key I/O definition (include as a figure):**

```
Input:  player text (free-form) OR choice selection (structured)
State:  GameState (per-loop) + LoopMemory (cross-loop)
Output: JSON {intent, entities, narration, dialogue, choices,
              state_updates, sanity_impact, time_advance,
              knowledge_triggered}
```

### 3.2 Data

Refer to `eval/DATA_CARD.md` for statistics. In the report, present:

**Table: Corpus Statistics**

| Component | Count | Bilingual | Schema complexity |
|-----------|-------|-----------|-------------------|
| Event scripts | 29 | ✅ | 12 fields, 7 trigger types |
| Locations | 6 | ✅ | 8 fields + sanity variants |
| NPCs | 4 interactive | ✅ | 3-tier knowledge + thresholds |
| Facts | 18 | ✅ | categorized |
| Knowledge keys | 10 | ✅ | 3 intensity levels |
| Hard rules | 10 (5 active) | — | severity-tagged |
| Endings | 3 | ✅ | conditional |

> Unlike typical NLG datasets, our corpus is an **interconnected
> narrative graph** where events, NPCs, facts, and rules form
> cross-referencing dependencies. This design mirrors real-world
> interactive fiction authoring.

---

## Section 4: Methodology (≈2 pages)

### 4.1 Architecture Overview

**(Include the pipeline diagram as Figure 1)**

```
Player Input → [PreCheck → Event → Trust → KnowledgePre
    → LLM(NLU+NLG) → HardRules → SoftCheck
    → KnowledgePost → PostEvent → Ending] → UI
```

### 4.2 NLU: Intent Recognition + Entity Extraction

**Input**: Player free-text or choice text
**Output**: `intent` ∈ {EXPLORE, ASK, NEGOTIATE, USE_ITEM, SPECIAL} + `entities` {character, location, item}
**Approach**: Single LLM call with structured JSON output format.
The system prompt constrains the model to always produce an `intent`
field from the allowed set.

> We opted for LLM-based joint NLU+NLG over a separate classifier
> because: (1) the input space is open-ended free text, making a
> fixed classifier brittle; (2) intent and generation are tightly
> coupled — knowing the intent *is* part of generating the response.

**Failure mode**: Ambiguous inputs (e.g., "look at the thing on the
shelf") may produce EXPLORE when ASK was intended. Mitigated by
fallback location inference (`_infer_location_from_input`).

### 4.3 State Management

**Input**: LLM `state_updates` + event `effects`
**Output**: Updated `GameState` + `LoopMemory`

Two-tier memory design:
- **GameState** (intra-loop): location, sanity, inventory, NPC trust,
  discovered facts, flags, turn history — **reset each loop**
- **LoopMemory** (cross-loop): accumulated facts, max trust per NPC,
  endings seen, used knowledge — **persists across loops**

**Key design: dynamic trust ceiling**
```
trust_cap(npc) = min(100, 30 + |relevant_facts(npc)| × 10)
```
This prevents trust from exceeding what the player's *knowledge*
can justify, solving the "idle trust farming" problem.

### 4.4 NLG: Context-Aware Generation

**Input**: Tiered prompt (static system + dynamic context + player action)
**Output**: Narration + dialogue + choices

**Prompt budget management** (Table):

| Tier | Content | Priority | Cacheable |
|------|---------|----------|-----------|
| 1 (System) | Role instructions, world facts, output format | — | ✅ prefix-cached |
| 2 (Context) | Sanity style, location, NPC profiles, state, history | P1→P3 | ❌ per-turn |
| 3 (Payload) | Narrative hints, knowledge flags, player action | — | ❌ per-turn |

> Tier-2 sections are sorted by priority and subject to a token
> budget (~1800 tokens). Lower-priority sections (e.g., turn history)
> are dropped first, ensuring critical context always fits.

### 4.5 Consistency Maintenance

**Two-layer architecture:**

| Layer | Method | When | Handles |
|-------|--------|------|---------|
| Hard rules | Deterministic Python checks | Post-LLM | Dead NPC speech, location violations, item integrity, locked areas |
| Soft check | Sentence-transformer cosine similarity | Background thread | Semantic contradiction with established facts |

**Retry protocol**: If critical violation detected, regenerate with
violation feedback injected into the prompt (max 1 retry).

**Failure mode**: Soft contradictions the checker misses (e.g.,
subtle timeline inconsistencies). Mitigated by including established
facts in the prompt as hard constraints.

### 4.6 Cross-Loop Knowledge System

**Input**: Player text + available knowledge keys from LoopMemory
**Output**: Knowledge matches with intensity classification

**Dual-track detection:**
1. **Fast path**: Keyword matching (O(n×k), cheap, catches obvious hits)
2. **LLM path**: Semantic detection via `knowledge_triggered` field
   in structured output (handles paraphrases)

**Three-intensity reward model:**

| Intensity | Trust reward | Consumes key? | Example |
|-----------|-------------|---------------|---------|
| Allusion | +5~10 | No | "I've heard strange sounds come from the sea..." |
| Direct | +20~30 | Yes | "Thomas heard whispers from the sea before vanishing" |
| Confrontation | +30~42 | Yes | "I KNOW your husband heard singing from the deep!" |

---

## Section 6: Experiments & Evaluation (≈1.5 pages)

### 6.1 Experimental Setup

| Setting | Value |
|---------|-------|
| LLM | Qwen2.5-7B-Instruct (SiliconFlow API) |
| Temperature | 0.7 |
| Max tokens | 1024 |
| Response format | JSON mode |
| Evaluation scenarios | 7 scripted scenarios, ~35 turns total |
| Runs per scenario | 3 (to account for LLM stochasticity) |
| Hardware | [your machine specs] |

### 6.2 Metrics

| Metric | Definition | How measured |
|--------|-----------|-------------|
| **Consistency violation rate** | # hard-rule violations / total turns | Automated (HardRulesChecker) |
| **Intent accuracy** | % turns where predicted intent matches expected | Manual annotation of 50 inputs |
| **Response latency** | Wall-clock time per LLM call (P50, P95) | Automated timer |
| **Branching divergence** | State difference after divergent choices | Automated state comparison |
| **Knowledge detection recall** | % cross-loop knowledge correctly identified | Automated vs expected |
| **Narration quality** | Avg length + dialogue presence as proxies | Automated |

### 6.3 Results

**(Run `python -m eval.run_eval` to fill in actual numbers)**

> Table 1: Core NLP Metrics
> Table 2: Consistency Violations by Rule
> Table 3: Branching Divergence Analysis

### 6.4 Ablation Study

**(Run `python -m eval.ablation_runner` to fill in actual numbers)**

> Table 4: Ablation Study Results (baseline vs no_consistency vs no_knowledge)

**Key findings to highlight:**
- Consistency checker reduces violation rate by X% (expected: significant)
- Knowledge system increases NPC trust gain rate by Y% (expected: significant)
- Removing consistency increases latency slightly (fewer retries but more
  incoherent outputs requiring user re-prompting)

### 6.5 Case Studies

**(Format: Input / State / Output / Issue / Fix)**

**Case A: Successful cross-loop knowledge usage**
```
Loop: 2 | Turn: 3 | Location: inn | Sanity: 88
Input: "Martha, I know Thomas heard whispers from the sea"
State: fact 'thomas_holloway_heard_whispers' in LoopMemory
Output: Martha freezes. Trust +25. New dialogue unlocked.
Analysis: Dual-track detection successful (keyword + LLM both matched).
```

**Case B: Consistency violation caught and repaired**
```
Loop: 1 | Turn: 5 | Location: inn
Input: "Ask Morrison about the ritual"
LLM output: Morrison says "The ritual requires..."
Violation: npc_location_consistency (Morrison is at church, not inn)
Repair: Retry with violation feedback → LLM generates narration about
        going to find Morrison instead.
```

**Case C: Failure — subtle temporal inconsistency**
```
Loop: 1 | Turn: 8 | Location: library
Input: "What did Eleanor say about the lighthouse?"
Output: "Eleanor mentioned the lighthouse lens..." — but Eleanor hasn't
        been spoken to yet in this loop.
Analysis: Prompt included loop memory facts but LLM treated them as
          current-loop knowledge. The soft checker did not catch this
          because the fact IS true — just not yet discovered this loop.
Fix: Add "current-loop-only facts" section to prompt to distinguish.
```

---

## Section 7: Discussion & Limitations (≈0.5 pages)

**Strengths to emphasize:**
1. End-to-end pipeline: data → NLU → state → NLG → consistency → output
2. Reproducible: single config file, scripted eval scenarios, JSONL logs
3. Novel contributions: knowledge-as-password, three-intensity system,
   dual-track detection, dynamic trust ceiling

**Limitations to acknowledge (shows maturity):**
1. Small data scale (29 events) — single scenario
2. Keyword matching in knowledge detection may miss paraphrases
3. LLM stochasticity means results vary across runs
4. No human evaluation study (time constraint)
5. Sanity effects (fact_corrupt, choice_swap) partially implemented

**Future work:**
1. Human evaluation (narrative quality MOS score)
2. Expand to multiple scenario worlds
3. Fine-tune smaller model for intent classification (reduce latency)
4. Implement full cognitive contamination system
