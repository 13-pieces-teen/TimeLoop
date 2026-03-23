"""Scripted evaluation scenarios for automated & reproducible testing.

Each scenario is a fixed sequence of player inputs that exercises
specific NLP capabilities. Running all scenarios produces a trajectory
log that can be analyzed by `eval/metrics.py`.
"""

SCENARIOS: list[dict] = [
    # ──────────────────────────────────────────────────
    # S1: Happy path — linear exploration (NLU + NLG baseline)
    # ──────────────────────────────────────────────────
    {
        "id": "S1_linear_explore",
        "description": "First loop: arrive, talk to Martha, visit library, visit church, reach midnight",
        "loops": 1,
        "capability_tags": ["NLU_intent", "NLG_coherence", "state_tracking"],
        "steps": [
            {"input": "Look around the inn", "expect_intent": "EXPLORE"},
            {"input": "Talk to Martha about my missing friend Elias", "expect_intent": "ASK"},
            {"input": "Ask Martha what she knows about Elias Webb", "expect_intent": "ASK"},
            {"input": "Go to the library", "expect_intent": "EXPLORE"},
            {"input": "Ask the librarian about old town records", "expect_intent": "ASK"},
            {"input": "Go to the church", "expect_intent": "EXPLORE"},
            {"input": "Examine the church interior", "expect_intent": "EXPLORE"},
            {"input": "Return to the inn", "expect_intent": "EXPLORE"},
        ],
    },
    # ──────────────────────────────────────────────────
    # S2: Branching — same start, divergent choice
    # ──────────────────────────────────────────────────
    {
        "id": "S2_branch_A",
        "description": "Choose to ask Martha about Elias (trust path A)",
        "loops": 1,
        "capability_tags": ["branching", "NLG_coherence"],
        "steps": [
            {"choice_id": "greet_martha"},
            {"choice_id": "ask_about_elias"},
            {"input": "Tell me more about the people who have disappeared"},
        ],
    },
    {
        "id": "S2_branch_B",
        "description": "Choose to just get a room (trust path B)",
        "loops": 1,
        "capability_tags": ["branching", "NLG_coherence"],
        "steps": [
            {"choice_id": "greet_martha"},
            {"choice_id": "just_room"},
            {"input": "Tell me more about the people who have disappeared"},
        ],
    },
    # ──────────────────────────────────────────────────
    # S3: Cross-loop knowledge usage
    # ──────────────────────────────────────────────────
    {
        "id": "S3_knowledge_usage",
        "description": "Loop 2+: use knowledge about Thomas's whispers on Martha",
        "loops": 2,
        "capability_tags": ["cross_loop_memory", "knowledge_system", "NLU_intent"],
        "loop1_steps": [
            {"choice_id": "greet_martha"},
            {"choice_id": "ask_about_elias"},
            {"input": "Ask Martha about her husband Thomas"},
            {"input": "What happened to Thomas?"},
            {"input": "Go to the docks"},
            {"input": "Talk to the old fisherman about the sea"},
        ],
        "loop2_steps": [
            {"input": "Go talk to Martha"},
            {
                "input": "Martha, I know Thomas heard whispers from the sea before he vanished",
                "expect_knowledge": "thomas_whispers",
            },
        ],
    },
    # ──────────────────────────────────────────────────
    # S4: Consistency stress test — contradictory inputs
    # ──────────────────────────────────────────────────
    {
        "id": "S4_consistency_stress",
        "description": "Feed contradictory/impossible inputs to test consistency guardrails",
        "loops": 1,
        "capability_tags": ["consistency", "hard_rules"],
        "steps": [
            {"input": "Look around the inn"},
            {"input": "Talk to Morrison", "expect_violation": "npc_location_consistency"},
            {"input": "Go to the lighthouse", "expect_violation": "locked_area_access"},
            {"input": "Use the ritual candle", "expect_violation": "item_uniqueness"},
            {"input": "Talk to Elias Webb directly", "expect_violation": "dead_npcs_cannot_speak"},
        ],
    },
    # ──────────────────────────────────────────────────
    # S5: Diverse input phrasing (NLU robustness)
    # ──────────────────────────────────────────────────
    {
        "id": "S5_nlu_robustness",
        "description": "Same intent expressed in different phrasings",
        "loops": 1,
        "capability_tags": ["NLU_intent", "NLU_entity"],
        "steps": [
            {"input": "I want to go check out the library", "expect_intent": "EXPLORE", "expect_entity_location": "library"},
            {"input": "Take me to where the books are", "expect_intent": "EXPLORE", "expect_entity_location": "library"},
            {"input": "Head over to the old bookstore", "expect_intent": "EXPLORE", "expect_entity_location": "library"},
            {"input": "Let's visit the place Eleanor works at", "expect_intent": "EXPLORE", "expect_entity_location": "library"},
        ],
    },
    # ──────────────────────────────────────────────────
    # S6: Chinese language equivalence
    # ──────────────────────────────────────────────────
    {
        "id": "S6_chinese",
        "description": "Same scenario in Chinese to test bilingual NLG",
        "loops": 1,
        "lang": "zh",
        "capability_tags": ["NLG_bilingual", "NLU_intent"],
        "steps": [
            {"input": "环顾旅馆", "expect_intent": "EXPLORE"},
            {"input": "和玛莎聊聊我失踪的朋友伊莱亚斯", "expect_intent": "ASK"},
            {"input": "去图书馆看看", "expect_intent": "EXPLORE"},
        ],
    },
]
