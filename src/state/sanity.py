from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class SanitySystem:
    """Manages sanity value and maps it to narrative style directives."""

    def __init__(self, styles_path: str | Path):
        with open(styles_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.styles: list[dict[str, Any]] = []
        for key, style in data.get("styles", {}).items():
            self.styles.append(
                {
                    "id": key,
                    "name": style["name"],
                    "range_min": style["range"][0],
                    "range_max": style["range"][1],
                    "directive": style["directive"].strip(),
                    "example": style.get("example", "").strip(),
                }
            )
        self.styles.sort(key=lambda s: s["range_min"], reverse=True)

    def get_style(self, sanity: int) -> dict[str, Any]:
        for style in self.styles:
            if style["range_min"] <= sanity <= style["range_max"]:
                return style
        return self.styles[-1]

    def get_directive(self, sanity: int) -> str:
        style = self.get_style(sanity)
        return (
            f"CURRENT SANITY LEVEL: {sanity}/100 ({style['name']})\n"
            f"NARRATIVE STYLE DIRECTIVE:\n{style['directive']}"
        )

    def get_style_name(self, sanity: int) -> str:
        return self.get_style(sanity)["name"]
