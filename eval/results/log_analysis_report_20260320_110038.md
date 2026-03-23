# TimeLoop — Evaluation Report

*Generated: 2026-03-20 11:00*
*Data source: 219 turns across 3 session(s)*

---

## 1. Experimental Setup

| Setting | Value |
|---------|-------|
| LLM Model | Qwen/Qwen2.5-7B-Instruct |
| API Provider | SiliconFlow |
| Temperature | 0.7 |
| Max Tokens | 1024 |
| Response Format | JSON mode |
| Consistency Checker | HardRulesChecker (5 active rules) |
| Soft Checker | Disabled (dev-only) |
| Total Turns Evaluated | 219 |
| Sessions | 3 |
| Max Loop Reached | 6 |

## 2. NLU Performance — Intent Recognition

### 2.1 Intent Distribution

| Intent | Count | Percentage |
|--------|-------|------------|
| TALK | 122 | 55.7% |
| INVESTIGATE | 43 | 19.6% |
| EXPLORE | 28 | 12.8% |
| UNKNOWN | 8 | 3.7% |
| USE_ITEM | 7 | 3.2% |
| WAIT | 5 | 2.3% |
| SHOW | 1 | 0.5% |
| MOVE | 1 | 0.5% |
| FLEE | 1 | 0.5% |
| ACTION | 1 | 0.5% |
| EXAMINE | 1 | 0.5% |
| READ | 1 | 0.5% |

**Unique intent types detected**: 12

### 2.2 Input Type Breakdown

| Input Type | Count | Percentage |
|------------|-------|------------|
| Scripted Event | 0 | 0.0% |
| Choice-Driven | 201 | 91.8% |
| Free-Text | 18 | 8.2% |

> The system handles three input modalities: scripted events (auto-triggered),
> player choice selections, and free-form natural language input.
> Free-text inputs require full NLU pipeline (intent + entity extraction).

## 3. NLG Performance — Narrative Generation

### 3.1 Narration Statistics

| Metric | Value |
|--------|-------|
| Total narrations generated | 219 |
| Average length (chars) | 121 |
| Median length (chars) | 78 |
| Min length | 34 |
| Max length | 606 |

## 4. State Tracking & Consistency

### 4.1 State Update Summary

| Update Type | Count |
|-------------|-------|
| `set_flag` | 48 |
| `add_fact` | 47 |
| `update_trust` | 47 |
| `move_player` | 27 |
| `add_item` | 2 |
| `update_position` | 1 |
| **Total** | **172** |

### 4.2 Fact Discovery Progress

**Total unique facts discovered**: 41 / 18

| # | Fact ID | Loop | Turn |
|---|---------|------|------|
| 1 | `The player has booked a room for the night.` | 1 | 2 |
| 2 | `locket_is_a_reminder` | 1 | 8 |
| 3 | `thomas_holloway_heard_whispers` | 1 | 9 |
| 4 | `letters_on_desk` | 1 | 12 |
| 5 | `letters_from_webb` | 1 | 13 |
| 6 | `letters_reveal_elias_concerns` | 1 | 14 |
| 7 | `symbol_on_desk` | 1 | 15 |
| 8 | `symbol_on_desk_worn` | 1 | 16 |
| 9 | `locket_contains_photo_of_martha_and_thomas` | 1 | 18 |
| 10 | `room_furniture_description` | 2 | 3 |
| 11 | `Ravenhollow has fewer visitors than usual lately.` | 1 | 2 |
| 12 | `Martha is visibly affected when talking about Thomas Holloway` | 1 | 4 |
| 13 | `martha_noticed_unusual_quiet` | 1 | 12 |
| 14 | `fisherman_hears_whispers` | 1 | 15 |
| 15 | `伊莱亚斯博士在失踪前住在海风旅馆` | 1 | 4 |
| 16 | `玩家已经入住旅馆` | 1 | 2 |
| 17 | `玩家发现了伊莱亚斯·韦伯博士的信件` | 1 | 4 |
| 18 | `player_read_elias_letter` | 1 | 5 |
| 19 | `player_examined_letter` | 1 | 6 |
| 20 | `镇子最近访客减少，人们天黑后避免外出。` | 1 | 2 |
| 21 | `访客减少可能与天气和不安的预感有关` | 1 | 3 |
| 22 | `martha_necklace_from_thomas` | 1 | 7 |
| 23 | `town_quietness_reason` | 1 | 4 |
| 24 | `martha_plans_to_do_housework` | 1 | 8 |
| 25 | `found_abandoned_cottage` | 1 | 12 |
| 26 | `martha_docks_mention` | 1 | 6 |
| 27 | `old_silas_mentions_whispers` | 1 | 7 |
| 28 | `map_investigated` | 2 | 6 |
| 29 | `elias_thoughts_on_whispers` | 2 | 10 |
| 30 | `opened_thomas_letter` | 6 | 5 |
| 31 | `thomas_map_symbols` | 1 | 7 |
| 32 | `strange_events_mentioned` | 1 | 6 |
| 33 | `thomas_map_marks` | 1 | 7 |
| 34 | `promised_to_find_answers` | 1 | 5 |
| 35 | `glass_windows_history` | 1 | 7 |
| 36 | `morrison_warns_about_curiosity` | 1 | 8 |
| 37 | `_read_elias_letter` | 1 | 13 |
| 38 | `small_window_open` | 1 | 17 |
| 39 | `map_symbols_identified` | 1 | 5 |
| 40 | `martha_knows_the_symbol` | 1 | 6 |
| 41 | `photographed_book` | 2 | 15 |

### 4.3 NPC Trust Interactions

| NPC | Trust Updates | Total Δ | Avg Δ/Update |
|-----|-------------|---------|-------------|
| Martha Holloway | 12 | +0 | +0.0 |
| unknown | 34 | +0 | +0.0 |
| 玛莎·霍洛威 | 1 | +0 | +0.0 |

## 5. Spatial & Temporal Coverage

### 5.1 Location Visit Distribution

| Location | Turns Spent | Percentage |
|----------|-------------|------------|
| inn | 137 | 62.6% |
| church | 26 | 11.9% |
| lighthouse | 15 | 6.8% |
| docks | 11 | 5.0% |
| library | 9 | 4.1% |
| room | 7 | 3.2% |
| nearby_house | 4 | 1.8% |
| 镇子主街 | 3 | 1.4% |
| 小镇街道 | 2 | 0.9% |
| caves | 2 | 0.9% |
| town | 1 | 0.5% |
| street | 1 | 0.5% |
| outside_inn | 1 | 0.5% |

### 5.2 Sanity Level Distribution

| Sanity Level | Turns | Percentage |
|-------------|-------|------------|
| lucid | 203 | 92.7% |
| uneasy | 9 | 4.1% |
| distorted | 7 | 3.2% |
| madness | 0 | 0.0% |

**Sanity range**: 30 – 100 (mean: 93.3, median: 98)

## 6. Response Latency

| Metric | Value |
|--------|-------|
| Samples | 153 |
| **Mean** | **20191 ms** |
| **Median (P50)** | **15654 ms** |
| P95 | 46939 ms |
| Min | 5701 ms |
| Max | 55596 ms |

> Latency measured as wall-clock time between consecutive turns
> (filtered to 100ms–60s range to exclude idle time).

## 7. Cross-Loop Memory & Branching

**Loops completed**: 6 unique loops
**Max loop reached**: 6

### Location Sequences by Loop

- **loop_1**: inn → town → inn → 镇子主街 → inn → room → street → inn → outside_inn → nearby_house → inn → docks → inn → library → inn → church → lighthouse → inn → caves → inn → church
- **loop_2**: inn → 小镇街道 → inn → lighthouse → inn → library → inn → church → inn → library
- **loop_3**: inn → docks → inn → docks
- **loop_4**: docks → caves → inn
- **loop_5**: church
- **loop_6**: inn

> **Branching diversity**: 6 unique location sequences out of 6 loops (100% unique)

## 8. Consistency Performance

### 8.1 Hard Rules Coverage

| Rule ID | Severity | Implementation | Status |
|---------|----------|----------------|--------|
| `dead_npcs_cannot_speak` | critical | Python check | Active |
| `npc_location_consistency` | critical | Python check | Active |
| `item_uniqueness` | critical | Python check | Active |
| `locked_area_access` | critical | Python check | Active |
| `sanity_bounds` | critical | Engine-enforced | Active (clamping) |
| `trust_gated_information` | high | Prompt-enforced | Active (NPC profiles) |
| `fact_consistency` | critical | Prompt-enforced | Active (established facts in prompt) |
| `time_progression` | high | Engine-enforced | Active (advance_time) |
| `location_knowledge` | high | Prompt-enforced | Partial |
| `loop_memory_persistence` | critical | Engine-enforced | Active (LoopMemory) |

> **10/10 rules** are enforced through a combination of deterministic Python checks (4),
> engine-level invariants (3), and prompt-injected constraints (3).
> Deterministic checks run post-LLM-generation and trigger retry on critical violations.

## 9. System Architecture Summary

```
Player Input
    │
    ▼
┌──────────────────────────────────────────┐
│  1. PreCheckProcessor     (midnight/event)│
│  2. EventProcessor        (scripted)      │
│  3. TrustProcessor        (passive trust) │
│  4. KnowledgePreProcessor (inject context)│
│  5. LLMProcessor          (NLU + NLG)     │
│     ├─ HardRulesChecker   (post-check)    │
│     └─ SoftChecker        (background)    │
│  6. KnowledgePostProcessor(settle trust)  │
│  7. PostEventProcessor    (late events)   │
│  8. EndingProcessor       (check endings) │
└──────────────────────────────────────────┘
    │
    ▼
TurnResult → Gradio UI
```

## 10. Case Studies

*(Selected from trajectory logs)*
### Case B: Free-Text NLU + NLG Success

- **Loop**: 1 | **Turn**: 17 | **Location**: inn
- **Sanity**: 95
- **Input**: `Excuse yourself to examine the room further.`
- **Predicted Intent**: `EXPLORE`
- **Narration** (excerpt): *The room is dimly lit by the gas lamps outside the inn's windows, casting long shadows across the floor. The bed is neatly made with a faded quilt, and the desk holds a flickering oil lamp and a small, worn locket....*
- **State Updates**: `[{"type": "set_flag", "flag": "bed_inspected", "value": false}]`

> **Analysis**: The LLM correctly classified the free-text input into the appropriate
> intent category and generated a narration that reflects the current game state,
> including location context and NPC presence.

### Case C: Failure Mode — Truncated Generation

- **Loop**: 1 | **Turn**: 3 | **Location**: inn
- **Input**: `她似乎在害怕。温和地追问更多细节。`
- **Narration**: *玛莎的眼神移开了，她迅速地用抹布擦拭着柜台，试图掩盖自己的不安，但她那紧张的动作暴露了她的情绪。*

> **Analysis**: The LLM produced an unusually short narration, likely due to JSON
> truncation or max_tokens constraint. The `_try_repair_truncated_json` function in
> `output_parser.py` attempts to salvage partial outputs. **Mitigation**: Increased
> max_tokens budget and added last-resort narration extraction regex.
