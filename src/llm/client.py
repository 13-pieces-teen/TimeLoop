from __future__ import annotations

import json
import logging
import os
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """Wrapper around any OpenAI-compatible chat API (OpenAI, SiliconFlow, DeepSeek, etc.)."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.8,
        max_tokens: int = 1024,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
        resolved_url = base_url or os.environ.get("OPENAI_BASE_URL")

        kwargs: dict[str, Any] = {"api_key": resolved_key}
        if resolved_url:
            kwargs["base_url"] = resolved_url

        self.client = OpenAI(**kwargs)
        logger.info("LLM client: model=%s, base_url=%s", model, resolved_url or "(default)")

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        response_format: dict | None = None,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        logger.debug("LLM response tokens: %s", response.usage)
        return content

    def chat_json(self, system_prompt: str, user_message: str) -> dict:
        raw = self.chat(
            system_prompt,
            user_message,
            response_format={"type": "json_object"},
        )
        return json.loads(raw)
