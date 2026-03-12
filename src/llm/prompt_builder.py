from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.state.game_state import GameState
from src.state.loop_memory import LoopMemory
from src.state.sanity import SanitySystem


class PromptBuilder:
    """Assembles the multi-layer prompt for each game turn."""

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

    def _get_npc_injection(self, game_state: GameState, lang: str = "en") -> str:
        location = game_state.location
        profiles = self.npc_profiles.get(lang, self.npc_profiles["en"])
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
        loc_data = self.world_data.get("locations", {}).get(game_state.location, {})
        if not loc_data:
            return f"You are at: {game_state.location}"

        name_key = "name_zh" if lang == "zh" else "name"
        desc_key = "description_zh" if lang == "zh" else "description"
        loc_name = loc_data.get(name_key, loc_data.get("name", game_state.location))
        base_desc = loc_data.get(desc_key, loc_data.get("description", ""))

        sanity_notes = loc_data.get("sanity_notes", {})
        level = game_state.sanity_level
        label = "当前位置" if lang == "zh" else "CURRENT LOCATION"

        if level == "lucid":
            return f"{label}: {loc_name}\n{base_desc}"

        note_key = f"{level}_zh" if lang == "zh" else level
        extra = sanity_notes.get(note_key, sanity_notes.get(level, sanity_notes.get("uneasy", "")))
        overlay_label = "理智叠加效果" if lang == "zh" else "Sanity overlay"
        return (
            f"{label}: {loc_name}\n"
            f"{base_desc}\n"
            f"[{overlay_label}: {extra}]"
        )

    def _get_consistency_constraints(self, game_state: GameState, lang: str = "en") -> str:
        facts = game_state.discovered_facts
        if not facts:
            return "尚无已确立的事实。" if lang == "zh" else "No established facts yet."
        header = "已确立事实（绝不可违背）：" if lang == "zh" else "ESTABLISHED FACTS (must not contradict):"
        return header + "\n" + "\n".join(f"- {f}" for f in facts)

    def _get_turn_history_summary(self, game_state: GameState, lang: str = "en") -> str:
        if not game_state.turn_history:
            return "本轮循环暂无先前行动。" if lang == "zh" else "No previous actions this loop."
        lines = []
        for i, turn in enumerate(game_state.turn_history):
            player_action = turn.get("player_input", "?")
            narration_snippet = turn.get("narration", "")[:100]
            lines.append(f"Turn {i + 1}: Player: \"{player_action}\" -> {narration_snippet}...")
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

    def build_system_prompt(
        self, game_state: GameState, loop_memory: LoopMemory, lang: str = "en",
    ) -> str:
        system_base = self.system_base.get(lang, self.system_base["en"])
        sanity_sys = self.sanity_system.get(lang, self.sanity_system["en"])

        sec = lambda zh, en: zh if lang == "zh" else en

        parts = [
            system_base,
            "",
            *self._get_world_background(lang),
            "",
            f"--- {sec('理智风格', 'SANITY STYLE')} ---",
            sanity_sys.get_directive(game_state.sanity),
            "",
            f"--- {sec('当前位置', 'LOCATION')} ---",
            self._get_location_context(game_state, lang),
            "",
            f"--- {sec('NPC 档案', 'NPC PROFILES')} ---",
            self._get_npc_injection(game_state, lang) or sec("（此地点无NPC）", "(No NPCs at this location)"),
            "",
            f"--- {sec('世界状态', 'WORLD STATE')} ---",
            game_state.to_prompt_summary(),
            "",
            f"--- {sec('循环记忆', 'LOOP MEMORY')} ---",
            loop_memory.to_prompt_summary(),
            "",
            f"--- {sec('一致性约束', 'CONSISTENCY CONSTRAINTS')} ---",
            self._get_consistency_constraints(game_state, lang),
            "",
            f"--- {sec('回合历史', 'TURN HISTORY')} ---",
            self._get_turn_history_summary(game_state, lang),
        ]
        return "\n".join(parts)

    def build_user_message(self, player_input: str) -> str:
        return f"Player action: {player_input}"

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
        """Build the prompt for the very first turn of a loop."""
        system = self.build_system_prompt(game_state, loop_memory, lang=lang)

        recap = self._build_loop_recap(loop_memory, lang)
        if recap:
            system += "\n\n" + recap

        if lang == "zh":
            if loop_memory.total_loops == 0:
                user_msg = (
                    "玩家刚刚第一次抵达雷文霍洛。生成开场叙述：描述黄昏时分抵达旅馆、"
                    "小镇的氛围、以及与玛莎的第一次互动。这是故事的开始。"
                )
            else:
                user_msg = (
                    f"循环已重置。这是第{loop_memory.total_loops + 1}次循环。"
                    "玩家在晚上8点醒来，站在旅馆门口，手中握着伊莱亚斯的信。"
                    "他们拥有前几次循环的碎片记忆——某些场景似曾相识，某些面孔莫名熟悉。"
                    "生成沉浸式的循环重启叙述，融入既视感元素。"
                )
        else:
            if loop_memory.total_loops == 0:
                user_msg = (
                    "The player has just arrived in Ravenhollow for the first time. "
                    "Generate the opening narration: describe the arrival at the inn at dusk, "
                    "the atmosphere of the town, and the first interaction with Martha. "
                    "This is the beginning of the story."
                )
            else:
                user_msg = (
                    f"The loop has reset. This is loop #{loop_memory.total_loops + 1}. "
                    "The player wakes at the inn's doorstep at 8 PM, clutching Elias's letter. "
                    "They carry fragmented memories from previous loops — certain scenes feel "
                    "hauntingly familiar, certain faces stir unnameable recognition. "
                    "Generate an immersive loop-restart narration woven with deja vu."
                )
        return system, user_msg
