# Data Card: TimeLoop Narrative Corpus

## Overview

| Property | Value |
|----------|-------|
| **Corpus name** | TimeLoop Interactive Narrative Corpus (TINC) |
| **Domain** | Lovecraftian horror / time-loop fiction |
| **Languages** | English, Simplified Chinese (parallel bilingual) |
| **Format** | Structured YAML with cross-referenced IDs |
| **Annotation** | Manual expert annotation (3 annotators, ~40 person-hours) |
| **License** | Academic use only (COMP5423 course project) |

## Data Components

### 1. Event Scripts (`events.yaml`)

| Property | Value |
|----------|-------|
| Total events | 29 |
| Acts covered | 5 acts + midnight events |
| Avg narration length (EN) | ~85 words |
| Avg narration length (ZH) | ~120 characters |
| Avg choices per event | 2.8 |
| Events with dialogue | 18 (62%) |
| Events with images | 22 (76%) |

**Schema per event:**
```yaml
- id: string            # unique identifier
  act: int              # narrative act (1-5)
  title / title_zh: str # bilingual title
  trigger:              # structured trigger conditions
    location: str       # required location
    flag / not_flag: str # prerequisite flags
    npc_trust: {npc: threshold}
    fact_required: str  # cross-loop fact dependency
    min_loop: int       # minimum loop number
    any_input_keyword: [str]  # NLU keyword triggers
  narration / narration_zh: str  # bilingual narration text
  dialogue:             # optional NPC dialogue
    speaker / speaker_zh: str
    text / text_zh: str
  effects: [{type, ...}]  # state mutations
  choices: [{id, text, text_zh, sanity_cost, trust_bonus}]
```

**Trigger condition taxonomy:**
| Trigger type | Count | Description |
|-------------|-------|-------------|
| `auto` | 1 | Fires on game start |
| `location` | 14 | Player at specific location |
| `npc_trust` | 7 | NPC trust ≥ threshold |
| `fact_required` | 5 | Requires cross-loop fact |
| `min_loop` | 5 | Requires loop ≥ N |
| `any_input_keyword` | 4 | NLU keyword match |
| `knowledge_combination` | 2 | Multiple knowledge keys |

### 2. World Model (`world.yaml`)

| Property | Value |
|----------|-------|
| Locations | 6 (inn, library, church, docks, lighthouse, caves) |
| Locked locations | 2 (lighthouse, caves) |
| Location connections | 12 directed edges |
| Sanity-variant descriptions | 4 per location (lucid/uneasy/distorted/madness) |

### 3. NPC Knowledge Base (`npcs.yaml`)

| Property | Value |
|----------|-------|
| Interactive NPCs | 4 (Martha, Morrison, Eleanor, Silas) |
| Referenced NPCs | 1 (Elias Webb — missing, not interactive) |
| Knowledge tiers per NPC | 3 (public / hidden / secret) |
| Trust thresholds defined | 4-6 per NPC |
| Total knowledge entries | 47 across all NPCs |

### 4. Fact Ontology (`descriptions.yaml`)

| Property | Value |
|----------|-------|
| Total facts | 18 |
| Fact categories | 4 (Elias, Ritual, Entity, NPC) |
| Items | 7 |
| All entries bilingual | Yes |

### 5. Consistency Rules (`hard_rules.yaml` + `hard_rules.py`)

| Property | Value |
|----------|-------|
| Rules defined (YAML) | 10 |
| Rules implemented (Python) | 5 active checks |
| Severity levels | 2 (critical, high) |
| Critical rules | 6 |

**Implemented rule checklist:**
| Rule | Type | Active |
|------|------|--------|
| `dead_npcs_cannot_speak` | NPC dialogue validation | ✅ |
| `npc_location_consistency` | Spatial consistency | ✅ |
| `item_uniqueness` | Inventory integrity | ✅ |
| `locked_area_access` | Progression gating | ✅ |
| `sanity_bounds` | Value clamping | ⚠️ (stub) |
| `trust_gated_information` | Information control | ❌ (prompt-enforced) |
| `fact_consistency` | Narrative coherence | ❌ (prompt-enforced) |
| `time_progression` | Temporal integrity | ❌ (engine-enforced) |
| `location_knowledge` | Spatial knowledge | ❌ (prompt-enforced) |
| `loop_memory_persistence` | Memory integrity | ❌ (engine-enforced) |

### 6. Cross-Loop Knowledge Registry (`loop_memory.py`)

| Property | Value |
|----------|-------|
| Knowledge keys | 10 |
| Target NPCs covered | 4/4 |
| Intensity levels | 3 (allusion / direct / confrontation) |
| Avg keywords per entry (EN) | 4.2 |
| Avg keywords per entry (ZH) | 4.0 |
| All entries bilingual | Yes |

### 7. Plot Graph (`plot_graph.yaml`)

| Property | Value |
|----------|-------|
| Endings | 3 (bad / normal / true) |
| Decision points | 4 |
| Fact dependency chains | 7 |
| Max dependency depth | 3 |

## Data Collection & Annotation Process

1. **Narrative design**: Story outline, character arcs, and plot graph designed based on Lovecraftian fiction conventions (Innsmouth, Dunwich parallels).
2. **Event scripting**: Each event hand-written with bilingual narration, trigger conditions, and state effects. Cross-referenced for internal consistency.
3. **Consistency annotation**: Hard rules derived from narrative constraints; each rule maps to a deterministic Python check or a prompt-enforced soft constraint.
4. **Knowledge engineering**: Cross-loop knowledge entries designed to create meaningful player agency across time loops. Keywords selected through iterative playtesting.
5. **Quality assurance**: 3-pass review — narrative coherence, trigger logic validation, bilingual alignment check.

## Preprocessing

- All YAML files are loaded at startup and validated against expected schemas
- NPC knowledge is stratified by trust thresholds at load time
- Event trigger conditions are compiled into a priority-sorted evaluation order
- Bilingual text pairs are stored in parallel fields (`*_zh` suffix convention)

## Known Limitations

- Small scale: 29 events covers ~3-5 hours of gameplay, not exhaustive
- Single scenario: one story world (expandable via additional YAML files)
- Bilingual quality: translations are manual but not back-translated for verification
- Knowledge keywords: hand-selected, may miss valid paraphrases (mitigated by LLM-based detection)
