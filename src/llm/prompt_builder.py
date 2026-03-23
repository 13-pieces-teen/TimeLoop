from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from src.state.game_state import GameState
from src.state.loop_memory import LoopMemory
from src.state.sanity import SanitySystem

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Tiered prompt assembly: static system | dynamic context | player action.

    Tier 1 — Static System  (system message, stable across turns → prefix-cacheable)
        Role instructions, output format, world background facts.

    Tier 2 — Dynamic Context (prepended to user message, priority-sorted)
        P1 (critical):  sanity style, location, NPC profiles
        P2 (important): world state, consistency facts, loop memory
        P3 (nice-to-have): recent turn history

    Tier 3 — Turn Payload   (appended to user message)
        Narrative hints, knowledge-usage flags, player action text.
    """

    def __init__(self, config_dir: str | Path):
        config_dir = Path(config_dir)
        prompts_dir = config_dir / "prompts"

        def _read(name: str) -> str:
            with open(prompts_dir / name, "r", encoding="utf-8") as f:
                return f.read().strip()

        def _yaml(path: Path) -> dict:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}

        self.system_base = {
            "en": _read("system.txt"),
            "zh": _read("system_zh.txt"),
        }

        self.npc_profiles = {
            "en": _yaml(prompts_dir / "npc_profiles.yaml").get("profiles", {}),
            "zh": _yaml(prompts_dir / "npc_profiles_zh.yaml").get("profiles", {}),
        }

        self.sanity_system = {
            "en": SanitySystem(prompts_dir / "sanity_styles.yaml"),
            "zh": SanitySystem(prompts_dir / "sanity_styles_zh.yaml"),
        }

        self.world_data = _yaml(Path("data") / "scenarios" / "world.yaml")
        self.npcs_full_data = _yaml(Path("data") / "scenarios" / "npcs.yaml").get("npcs", {})

    NPC_SANITY_BEHAVIOR = {
        "en": {
            "lucid": "",
            "uneasy": (
                "SANITY EFFECT: The player seems uneasy. Occasionally pause mid-sentence "
                "as if you heard something, or briefly lose your train of thought."
            ),
            "distorted": (
                "SANITY EFFECT — UNRELIABLE NPC: You MUST slip one subtle falsehood into "
                "this conversation — a wrong name, a wrong date, an event that never happened, "
                "or a person who doesn't exist. Do NOT mark which part is false. The player "
                "should not be able to tell."
            ),
            "madness": (
                "SANITY EFFECT — DEEPLY UNRELIABLE NPC: At least half of what you say should "
                "be fabricated, contradictory, or nonsensical. You may speak in riddles, quote "
                "things no one said, or describe memories that belong to someone else. The "
                "boundary between your voice and the narrator's voice is dissolving."
            ),
        },
        "zh": {
            "lucid": "",
            "uneasy": (
                "理智效果：玩家看起来不安。偶尔在说话时停顿，仿佛听到了什么，"
                "或者短暂地忘记自己在说什么。"
            ),
            "distorted": (
                "理智效果——不可靠的NPC：你必须在这次对话中混入一个细微的虚假细节——"
                "搞错名字、日期、编造一个不存在的事件或人物。不要标注哪部分是假的。"
                "玩家应该无法分辨真伪。"
            ),
            "madness": (
                "理智效果——严重不可靠的NPC：你说的话中至少一半应该是编造的、矛盾的或荒谬的。"
                "你可以说谜语、引用没人说过的话、描述属于别人的记忆。"
                "你的声音与叙述者的声音之间的界限正在溶解。"
            ),
        },
    }

    def _get_npc_injection(self, game_state: GameState, lang: str = "en") -> str:
        location = game_state.location
        profiles = self.npc_profiles.get(lang, self.npc_profiles["en"])
        san_level = game_state.sanity_level
        san_behavior = self.NPC_SANITY_BEHAVIOR.get(lang, self.NPC_SANITY_BEHAVIOR["en"]).get(san_level, "")

        injections = []
        for npc_id, npc in game_state.characters.items():
            if npc.location != location or not npc.alive:
                continue
            profile = profiles.get(npc_id)
            if not profile:
                continue

            npc_full = self.npcs_full_data.get(npc_id, {})
            available_knowledge = self._get_available_knowledge(npc_full, npc.trust)

            text = profile["system_injection"]
            text = text.replace("{trust}", str(npc.trust))
            text = text.replace("{available_knowledge}", available_knowledge)
            text = text.replace("{sanity_behavior}", san_behavior)
            if san_behavior and "{sanity_behavior}" not in profile["system_injection"]:
                text = text.rstrip() + "\n" + san_behavior
            injections.append(text)

        return "\n\n".join(injections)

    def _get_available_knowledge(self, npc_data: dict, trust: int) -> str:
        knowledge = npc_data.get("knowledge", {})
        thresholds = npc_data.get("trust_thresholds", {})

        available = list(knowledge.get("public", []))

        threshold_map = {int(k): v for k, v in thresholds.items()}
        accessible_thresholds = sorted(
            t for t in threshold_map if t <= trust
        )
        behaviors = []
        for t in accessible_thresholds:
            behaviors.append(f"At trust {t}: {threshold_map[t]}")

        hidden = knowledge.get("hidden", [])
        if trust >= 50:
            available.extend(hidden[: (trust - 50) // 20 + 1])
        secret = knowledge.get("secret", [])
        if trust >= 90:
            available.extend(secret)

        lines = ["Known facts she/he can mention: " + "; ".join(available)]
        if behaviors:
            lines.append("Behavior at current trust: " + behaviors[-1])
        return "\n".join(lines)

    def _get_location_context(self, game_state: GameState, lang: str = "en") -> str:
        all_locations = self.world_data.get("locations", {})
        loc_data = all_locations.get(game_state.location, {})
        if not loc_data:
            return f"You are at: {game_state.location}"

        name_key = "name_zh" if lang == "zh" else "name"
        desc_key = "description_zh" if lang == "zh" else "description"
        loc_name = loc_data.get(name_key, loc_data.get("name", game_state.location))
        base_desc = loc_data.get(desc_key, loc_data.get("description", ""))

        sanity_notes = loc_data.get("sanity_notes", {})
        level = game_state.sanity_level
        label = "当前位置" if lang == "zh" else "CURRENT LOCATION"

        parts: list[str] = [f"{label}: {loc_name}\n{base_desc}"]

        if level != "lucid":
            note_key = f"{level}_zh" if lang == "zh" else level
            extra = sanity_notes.get(note_key, sanity_notes.get(level, sanity_notes.get("uneasy", "")))
            overlay_label = "理智叠加效果" if lang == "zh" else "Sanity overlay"
            parts.append(f"[{overlay_label}: {extra}]")

        connected = loc_data.get("connected_to", [])
        if connected:
            dest_lines: list[str] = []
            for dest_id in connected:
                dest_data = all_locations.get(dest_id, {})
                dest_name = dest_data.get(name_key, dest_id)
                locked = dest_data.get("locked", False)
                npcs = dest_data.get("npcs_present", [])
                npc_hint = f" ({', '.join(npcs)})" if npcs else ""
                lock_mark = (" [locked]" if not lang == "zh" else " [已锁定]") if locked else ""
                dest_lines.append(f"  - {dest_id}: {dest_name}{npc_hint}{lock_mark}")
            header = "可前往的地点：" if lang == "zh" else "REACHABLE LOCATIONS:"
            parts.append(f"{header}\n" + "\n".join(dest_lines))

        stal = game_state.turns_at_location
        if stal >= 3:
            if lang == "zh":
                parts.append(
                    f"【地点滞留警告】玩家已在此位置连续停留 {stal} 回合。"
                    "你的3个选项中，至少1个必须是「前往其他地点」并附带 move_player。"
                )
            else:
                parts.append(
                    f"LOCATION STALENESS WARNING: Player has stayed here for {stal} consecutive turns. "
                    "At least 1 of your 3 choices MUST be traveling to a different location with a move_player state_update."
                )

        return "\n\n".join(parts)

    def _get_consistency_constraints(self, game_state: GameState, lang: str = "en") -> str:
        facts = game_state.discovered_facts
        if not facts:
            return "尚无已确立的事实。" if lang == "zh" else "No established facts yet."
        header = "已确立事实（绝不可违背）：" if lang == "zh" else "ESTABLISHED FACTS (must not contradict):"
        return header + "\n" + "\n".join(f"- {f}" for f in facts)

    def _get_turn_history_summary(self, game_state: GameState, lang: str = "en") -> str:
        if not game_state.turn_history:
            return "本轮循环暂无先前行动。" if lang == "zh" else "No previous actions this loop."
        recent = game_state.turn_history[-3:]
        offset = len(game_state.turn_history) - len(recent)
        lines = []
        for i, turn in enumerate(recent):
            player_action = turn.get("player_input", "?")
            narration_snippet = turn.get("narration", "")[:80]
            lines.append(f"T{offset + i + 1}: \"{player_action}\" -> {narration_snippet}...")
        header = "近期历史：" if lang == "zh" else "RECENT HISTORY:"
        return header + "\n" + "\n".join(lines)

    def _get_world_background(self, lang: str = "en") -> list[str]:
        if lang == "zh":
            return [
                "--- 世界背景事实（始终为真，绝不违背）---",
                "- 托马斯·霍洛威（玛莎的丈夫）已失踪6个月。他不在场。",
                "- 伊莱亚斯·韦伯博士已失踪3周。他不在镇上。",
                "- 小镇异常安静。大多数居民天黑后避免外出。",
                "- 时间是1927年，雷文霍洛，新英格兰偏远海滨小镇。",
                "- 玩家是波士顿大学的民俗学讲师。",
            ]
        return [
            "--- WORLD BACKGROUND FACTS (always true, NEVER contradict) ---",
            "- Thomas Holloway (Martha's husband) has been MISSING for 6 months. He is NOT present.",
            "- Dr. Elias Webb has been missing for 3 weeks. He is NOT present in town.",
            "- The town is unusually quiet. Most residents avoid going out after dark.",
            "- It is 1927 in Ravenhollow, a remote New England coastal town.",
            "- The player is a folklore lecturer from Boston University.",
        ]

    # ------------------------------------------------------------------
    # Tier 1 — Static system prompt (stable across turns)
    # ------------------------------------------------------------------

    def build_static_system(self, lang: str = "en") -> str:
        """Instructions + world background. Unchanged between turns → prefix-cacheable."""
        base = self.system_base.get(lang, self.system_base["en"])
        return "\n".join([base, "", *self._get_world_background(lang)])

    # ------------------------------------------------------------------
    # Tier 2 — Dynamic context (priority-sorted, budget-aware)
    # ------------------------------------------------------------------

    def build_turn_context(
        self,
        game_state: GameState,
        loop_memory: LoopMemory,
        lang: str = "en",
        max_tokens: int = 1800,
    ) -> str:
        """Assemble per-turn context sorted by priority.

        Sections are added in priority order; if *max_tokens* (rough estimate)
        would be exceeded, lower-priority sections are dropped and logged.
        """
        sec = lambda zh, en: zh if lang == "zh" else en
        sanity_sys = self.sanity_system.get(lang, self.sanity_system["en"])

        npc_text = (
            self._get_npc_injection(game_state, lang)
            or sec("（此地点无NPC）", "(No NPCs at this location)")
        )

        sections: list[tuple[int, str, str]] = [
            (1, sec("理智风格", "SANITY STYLE"),     sanity_sys.get_directive(game_state.sanity)),
            (1, sec("当前位置", "LOCATION"),          self._get_location_context(game_state, lang)),
            (1, sec("NPC 档案", "NPC PROFILES"),      npc_text),
            (2, sec("世界状态", "WORLD STATE"),        game_state.to_prompt_summary()),
            (2, sec("一致性约束", "CONSISTENCY"),       self._get_consistency_constraints(game_state, lang)),
            (2, sec("循环记忆", "LOOP MEMORY"),        loop_memory.to_prompt_summary()),
            (3, sec("回合历史", "TURN HISTORY"),        self._get_turn_history_summary(game_state, lang)),
        ]

        sections.sort(key=lambda s: s[0])

        included: list[str] = []
        est_tokens = 0
        for prio, label, content in sections:
            cost = self._estimate_tokens(content)
            if est_tokens + cost > max_tokens:
                logger.debug(
                    "Prompt budget reached (%d/%d); dropping [P%d] %s (%d tok)",
                    est_tokens, max_tokens, prio, label, cost,
                )
                continue
            included.append(f"--- {label} ---\n{content}")
            est_tokens += cost

        return "\n\n".join(included)

    # ------------------------------------------------------------------
    # Tier 3 — User message (context + extras + player action)
    # ------------------------------------------------------------------

    def build_user_message(
        self,
        player_input: str,
        game_state: GameState | None = None,
        loop_memory: LoopMemory | None = None,
        lang: str = "en",
        extra_context: str = "",
    ) -> str:
        """Combine dynamic context, extra hints, and player action."""
        parts: list[str] = []
        if game_state and loop_memory:
            parts.append(self.build_turn_context(game_state, loop_memory, lang))
        if extra_context:
            parts.append(extra_context)
        parts.append(f"Player action: {player_input}")
        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Backward-compatible helpers
    # ------------------------------------------------------------------

    def build_system_prompt(
        self, game_state: GameState, loop_memory: LoopMemory, lang: str = "en",
    ) -> str:
        """Legacy API — returns static system + dynamic context combined."""
        return (
            self.build_static_system(lang)
            + "\n\n"
            + self.build_turn_context(game_state, loop_memory, lang)
        )

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token estimate (works for mixed en/zh)."""
        return max(1, len(text) // 3)

    def _build_loop_recap(self, loop_memory: LoopMemory, lang: str = "en") -> str:
        """Build a recap block for loops > 0 to inject deja vu flavor."""
        if loop_memory.total_loops == 0:
            return ""

        recent_facts = loop_memory.discovered_facts[-5:]
        familiar_npcs = [
            npc_id for npc_id, trust in loop_memory.npc_max_trust.items()
            if trust >= 30
        ]

        if lang == "zh":
            lines = [
                "--- 循环记忆碎片（用于渲染既视感氛围）---",
                f"这是第 {loop_memory.total_loops + 1} 次循环。",
            ]
            if recent_facts:
                lines.append("模糊浮现的记忆碎片：" + "、".join(
                    f.replace("_", " ") for f in recent_facts
                ))
            if familiar_npcs:
                lines.append(f"以下NPC会让玩家产生似曾相识的熟悉感：{', '.join(familiar_npcs)}")
            if loop_memory.endings_seen:
                lines.append(f"前世的结局残影：{', '.join(loop_memory.endings_seen)}")
            lines.append(
                "将以上碎片自然融入叙述——角色微妙的停顿、一闪而过的画面、"
                "「我们……见过面吗？」式的暗示。不要直接告诉玩家这是循环。"
            )
        else:
            lines = [
                "--- LOOP MEMORY FRAGMENTS (use to render deja vu atmosphere) ---",
                f"This is loop #{loop_memory.total_loops + 1}.",
            ]
            if recent_facts:
                lines.append("Faint echoes from before: " + ", ".join(
                    f.replace("_", " ") for f in recent_facts
                ))
            if familiar_npcs:
                lines.append(f"These NPCs feel strangely familiar: {', '.join(familiar_npcs)}")
            if loop_memory.endings_seen:
                lines.append(f"Afterimages of past endings: {', '.join(loop_memory.endings_seen)}")
            lines.append(
                "Weave these fragments naturally — subtle pauses, fleeting visions, "
                "'Have we... met before?' moments. Do NOT tell the player this is a loop."
            )

        return "\n".join(lines)

    def build_opening_prompt(
        self, game_state: GameState, loop_memory: LoopMemory, lang: str = "en",
    ) -> tuple[str, str]:
        """Build the prompt for the very first turn of a loop.

        Returns (system, user) where *system* is the stable Tier-1 prompt and
        *user* contains Tier-2 context + loop recap + opening instruction.
        """
        system = self.build_static_system(lang)

        context = self.build_turn_context(game_state, loop_memory, lang)
        recap = self._build_loop_recap(loop_memory, lang)

        if lang == "zh":
            if loop_memory.total_loops == 0:
                action = (
                    "玩家刚刚第一次抵达雷文霍洛。生成开场叙述：描述黄昏时分抵达旅馆、"
                    "小镇的氛围、以及与玛莎的第一次互动。这是故事的开始。"
                )
            else:
                action = (
                    f"循环已重置。这是第{loop_memory.total_loops + 1}次循环。"
                    "玩家在晚上8点醒来，站在旅馆门口，手中握着伊莱亚斯的信。"
                    "他们拥有前几次循环的碎片记忆——某些场景似曾相识，某些面孔莫名熟悉。"
                    "生成沉浸式的循环重启叙述，融入既视感元素。"
                )
        else:
            if loop_memory.total_loops == 0:
                action = (
                    "The player has just arrived in Ravenhollow for the first time. "
                    "Generate the opening narration: describe the arrival at the inn at dusk, "
                    "the atmosphere of the town, and the first interaction with Martha. "
                    "This is the beginning of the story."
                )
            else:
                action = (
                    f"The loop has reset. This is loop #{loop_memory.total_loops + 1}. "
                    "The player wakes at the inn's doorstep at 8 PM, clutching Elias's letter. "
                    "They carry fragmented memories from previous loops — certain scenes feel "
                    "hauntingly familiar, certain faces stir unnameable recognition. "
                    "Generate an immersive loop-restart narration woven with deja vu."
                )

        user_parts = [context]
        if recap:
            user_parts.append(recap)
        user_parts.append(action)
        return system, "\n\n".join(user_parts)
