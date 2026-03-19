from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VALID_INTENSITIES = ("allusion", "direct", "confrontation")


@dataclass
class KnowledgeKey:
    """A piece of knowledge the player can actively *use* in conversation.

    ``trust_reward`` maps intensity level to trust gain:
      - allusion  : vague hint — small bonus, does NOT consume the knowledge
      - direct    : explicit reference — standard bonus, consumes knowledge
      - confrontation : accusatory / emotional — large bonus, consumes knowledge
    """

    id: str
    keywords_en: list[str]
    keywords_zh: list[str]
    description_en: str
    description_zh: str
    target_npc: str
    trust_reward: dict[str, int]
    trust_penalty_wrong_npc: int = -10
    required_fact: str = ""
    hint_en: str = ""
    hint_zh: str = ""

    def matches_input(self, text: str) -> bool:
        """Fast-path keyword check (kept as a cheap first pass)."""
        lower = text.lower()
        for kw in self.keywords_en + self.keywords_zh:
            if kw.lower() in lower:
                return True
        return False

    def reward_for(self, intensity: str) -> int:
        return self.trust_reward.get(intensity, self.trust_reward.get("direct", 20))

    @staticmethod
    def consumes(intensity: str) -> bool:
        return intensity != "allusion"


KNOWLEDGE_REGISTRY: list[dict[str, Any]] = [
    {
        "id": "thomas_whispers",
        "keywords_en": ["thomas", "whispers", "singing", "heard from the sea"],
        "keywords_zh": ["托马斯", "低语", "歌声", "海底", "听到"],
        "description_en": "Thomas Holloway heard singing or whispers from the sea before he vanished",
        "description_zh": "托马斯·霍洛威失踪前听到了来自海中的歌声或低语",
        "target_npc": "martha",
        "trust_reward": {"allusion": 8, "direct": 25, "confrontation": 35},
        "trust_penalty_wrong_npc": -5,
        "required_fact": "thomas_holloway_heard_whispers",
        "hint_en": "Thomas heard singing from beneath the sea before he vanished...",
        "hint_zh": "托马斯失踪前听到了海底传来的歌声……",
    },
    {
        "id": "thomas_missing_duration",
        "keywords_en": ["six months", "half a year", "thomas missing"],
        "keywords_zh": ["六个月", "半年", "托马斯失踪"],
        "description_en": "Thomas Holloway has been missing for six months",
        "description_zh": "托马斯·霍洛威已失踪六个月",
        "target_npc": "martha",
        "trust_reward": {"allusion": 5, "direct": 15, "confrontation": 22},
        "trust_penalty_wrong_npc": -3,
        "required_fact": "thomas_holloway_missing_six_months",
        "hint_en": "Thomas has been gone for six months now...",
        "hint_zh": "托马斯已经失踪六个月了……",
    },
    {
        "id": "ritual_30_years",
        "keywords_en": ["thirty years", "30 years", "cycle", "every generation"],
        "keywords_zh": ["三十年", "30年", "周期", "每一代"],
        "description_en": "The ritual repeats on a thirty-year cycle, once every generation",
        "description_zh": "仪式以三十年为周期重复，每一代人一次",
        "target_npc": "morrison",
        "trust_reward": {"allusion": 8, "direct": 25, "confrontation": 35},
        "trust_penalty_wrong_npc": -8,
        "required_fact": "ritual_happens_every_30_years",
        "hint_en": "The ritual repeats every thirty years...",
        "hint_zh": "仪式每三十年重复一次……",
    },
    {
        "id": "morrison_last_ritual",
        "keywords_en": ["arthur crane", "sacrifice", "last ritual", "you performed"],
        "keywords_zh": ["亚瑟·克莱恩", "祭品", "上一次仪式", "你执行"],
        "description_en": "Morrison personally performed the last ritual and sacrificed Arthur Crane",
        "description_zh": "莫里森亲自执行了上一次仪式，祭祀了亚瑟·克莱恩",
        "target_npc": "morrison",
        "trust_reward": {"allusion": 10, "direct": 30, "confrontation": 42},
        "trust_penalty_wrong_npc": -10,
        "required_fact": "morrison_performed_last_ritual",
        "hint_en": "Morrison sacrificed Arthur Crane thirty years ago...",
        "hint_zh": "莫里森三十年前祭祀了亚瑟·克莱恩……",
    },
    {
        "id": "morrison_locked_elias",
        "keywords_en": ["locked elias", "imprisoned", "lighthouse prison", "you locked him"],
        "keywords_zh": ["锁住伊莱亚斯", "关在灯塔", "囚禁", "你把他锁"],
        "description_en": "Morrison locked Elias Webb in the lighthouse to prevent him from interfering",
        "description_zh": "莫里森将伊莱亚斯·韦伯锁在灯塔中以阻止他干预",
        "target_npc": "morrison",
        "trust_reward": {"allusion": 10, "direct": 30, "confrontation": 42},
        "trust_penalty_wrong_npc": -5,
        "required_fact": "morrison_locked_elias_in_lighthouse",
        "hint_en": "Morrison locked Elias in the lighthouse...",
        "hint_zh": "莫里森把伊莱亚斯锁在了灯塔里……",
    },
    {
        "id": "eleanor_helped_elias",
        "keywords_en": ["restricted section", "you helped elias", "library access", "gave him access"],
        "keywords_zh": ["禁区", "你帮过伊莱亚斯", "图书馆权限", "让他进入"],
        "description_en": "Eleanor gave Elias access to the restricted section of the library",
        "description_zh": "埃莉诺让伊莱亚斯进入了图书馆的禁区",
        "target_npc": "eleanor",
        "trust_reward": {"allusion": 6, "direct": 20, "confrontation": 28},
        "trust_penalty_wrong_npc": -5,
        "required_fact": "eleanor_helped_elias",
        "hint_en": "Eleanor gave Elias access to the restricted section...",
        "hint_zh": "埃莉诺让伊莱亚斯进入了图书馆禁区……",
    },
    {
        "id": "elias_lens_theory",
        "keywords_en": ["lens", "refract", "permanent seal", "lighthouse lens", "alternative"],
        "keywords_zh": ["透镜", "折射", "永久封印", "灯塔透镜", "替代方法"],
        "description_en": "Elias believed the lighthouse lens could make the seal permanent through refraction",
        "description_zh": "伊莱亚斯认为灯塔透镜可以通过折射使封印永久化",
        "target_npc": "eleanor",
        "trust_reward": {"allusion": 8, "direct": 25, "confrontation": 35},
        "trust_penalty_wrong_npc": -5,
        "required_fact": "elias_discovered_lens_ritual",
        "hint_en": "Elias believed the lighthouse lens could make the seal permanent...",
        "hint_zh": "伊莱亚斯相信灯塔透镜可以让封印永久化……",
    },
    {
        "id": "entity_nature",
        "keywords_en": ["dreaming", "not evil", "sleeping god", "it dreams"],
        "keywords_zh": ["做梦", "并非邪恶", "沉睡", "它在梦"],
        "description_en": "The entity beneath the bay is dreaming, not actively malevolent",
        "description_zh": "海湾之下的存在是在做梦，并非主动施恶",
        "target_npc": "silas",
        "trust_reward": {"allusion": 8, "direct": 25, "confrontation": 35},
        "trust_penalty_wrong_npc": -8,
        "required_fact": "entity_is_dreaming_not_evil",
        "hint_en": "The entity beneath the bay is dreaming, not malevolent...",
        "hint_zh": "海湾之下的存在在做梦，并非恶意……",
    },
    {
        "id": "silas_witness",
        "keywords_en": ["you saw it", "water opened", "door in the sea", "you witnessed"],
        "keywords_zh": ["你见过它", "水面打开", "海中之门", "你亲眼目睹"],
        "description_en": "Silas personally witnessed the entity when the sea opened like a door thirty years ago",
        "description_zh": "西拉斯三十年前亲眼目睹了水面像门一样打开、显露出存在的景象",
        "target_npc": "silas",
        "trust_reward": {"allusion": 10, "direct": 30, "confrontation": 42},
        "trust_penalty_wrong_npc": -5,
        "required_fact": "silas_witnessed_the_entity",
        "hint_en": "Silas saw the entity thirty years ago — the water opened like a door...",
        "hint_zh": "西拉斯三十年前见过那个存在——水面像一扇门一样打开……",
    },
    {
        "id": "elias_alternative",
        "keywords_en": ["alternative method", "no sacrifice", "without sacrifice", "elias found a way"],
        "keywords_zh": ["替代方法", "不需要祭品", "无需牺牲", "伊莱亚斯找到了"],
        "description_en": "Elias discovered a way to seal the entity without human sacrifice",
        "description_zh": "伊莱亚斯发现了无需活人祭祀即可封印存在的方法",
        "target_npc": "eleanor",
        "trust_reward": {"allusion": 10, "direct": 30, "confrontation": 42},
        "trust_penalty_wrong_npc": -5,
        "required_fact": "elias_found_alternative_method",
        "hint_en": "Elias found a way to seal the entity without human sacrifice...",
        "hint_zh": "伊莱亚斯找到了不需要活人祭祀的封印方法……",
    },
]


@dataclass
class LoopMemory:
    total_loops: int = 0
    discovered_facts: list[str] = field(default_factory=list)
    unlocked_choices: list[str] = field(default_factory=list)
    endings_seen: list[str] = field(default_factory=list)
    npc_max_trust: dict[str, int] = field(default_factory=dict)
    last_loop_visited_locations: list[str] = field(default_factory=list)
    last_loop_new_facts: list[str] = field(default_factory=list)
    last_loop_npcs_talked: list[str] = field(default_factory=list)
    used_knowledge: list[str] = field(default_factory=list)

    @property
    def knowledge_keys(self) -> list[KnowledgeKey]:
        """Return usable knowledge keys based on discovered facts."""
        keys = []
        for entry in KNOWLEDGE_REGISTRY:
            if entry["required_fact"] in self.discovered_facts:
                keys.append(KnowledgeKey(**entry))
        return keys

    @property
    def unused_knowledge(self) -> list[KnowledgeKey]:
        return [k for k in self.knowledge_keys if k.id not in self.used_knowledge]

    def mark_knowledge_used(self, knowledge_id: str) -> None:
        if knowledge_id not in self.used_knowledge:
            self.used_knowledge.append(knowledge_id)

    def record_loop_end(self, game_state) -> None:
        """Absorb relevant info from the ending game state before reset."""
        self.total_loops += 1

        old_facts = set(self.discovered_facts)
        self.last_loop_new_facts = []
        for fact in game_state.discovered_facts:
            if fact not in self.discovered_facts:
                self.discovered_facts.append(fact)
            if fact not in old_facts:
                self.last_loop_new_facts.append(fact)

        self.last_loop_npcs_talked = [
            npc_id for npc_id, npc in game_state.characters.items()
            if npc.met and npc.alive
        ]

        self.last_loop_visited_locations = list(
            game_state.flags.get("_visited_locations", [])
        ) if isinstance(game_state.flags.get("_visited_locations"), list) else []

        for npc_id, npc in game_state.characters.items():
            prev_max = self.npc_max_trust.get(npc_id, 0)
            self.npc_max_trust[npc_id] = max(prev_max, npc.trust)

    def record_ending(self, ending_id: str) -> None:
        if ending_id not in self.endings_seen:
            self.endings_seen.append(ending_id)

    def unlock_choice(self, choice_id: str) -> None:
        if choice_id not in self.unlocked_choices:
            self.unlocked_choices.append(choice_id)

    def to_dict(self) -> dict:
        return {
            "total_loops": self.total_loops,
            "discovered_facts": self.discovered_facts,
            "unlocked_choices": self.unlocked_choices,
            "endings_seen": self.endings_seen,
            "npc_max_trust": self.npc_max_trust,
            "used_knowledge": self.used_knowledge,
            "available_knowledge": [k.id for k in self.knowledge_keys],
        }

    def to_prompt_summary(self) -> str:
        if self.total_loops == 0:
            return "This is your first loop. You have no prior memories."

        lines = [
            f"This is loop #{self.total_loops + 1}.",
            f"From previous loops, you remember: {', '.join(self.discovered_facts) or 'nothing yet'}.",
        ]
        if self.unlocked_choices:
            lines.append(
                f"Unlocked options from past experience: {', '.join(self.unlocked_choices)}."
            )
        if self.endings_seen:
            lines.append(
                f"You have a vague sense of deja vu about: {', '.join(self.endings_seen)}."
            )
        unused = self.unused_knowledge
        if unused:
            hints = [k.hint_en for k in unused[:3]]
            lines.append(
                f"Fragments of memory surface: {'; '.join(hints)}"
            )
        return "\n".join(lines)
