# -*- coding: utf-8 -*-
"""
Multi-provider AI client.
Supports Google Gemini, OpenAI, and Anthropic Claude.
Auto-detects provider from .env variables.
"""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()


def get_runtime_ai_config() -> dict:
    """Detect which AI provider is configured and return its config."""
    if os.getenv("GEMINI_API_KEY"):
        return {
            "provider": "gemini",
            "api_key_configured": True,
            "model": os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
            "configured_key_count": 1,
        }
    if os.getenv("OPENAI_API_KEY"):
        return {
            "provider": "openai",
            "api_key_configured": True,
            "model": os.getenv("OPENAI_MODEL", "gpt-4o"),
            "configured_key_count": 1,
        }
    if os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEYS"):
        keys = os.getenv("ANTHROPIC_API_KEYS", "")
        count = len(keys.split(",")) if keys else 1
        return {
            "provider": "anthropic",
            "api_key_configured": True,
            "model": os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307"),
            "configured_key_count": count,
        }

    return {
        "provider": "none",
        "api_key_configured": False,
        "model": "None",
        "configured_key_count": 0,
    }


async def call_ai(system_prompt: str, user_message: str) -> str:
    """Unified method to call any configured AI provider."""
    config = get_runtime_ai_config()

    if not config["api_key_configured"]:
        raise ValueError(
            "No API key found. Add one of these to backend/.env:\n"
            "  GEMINI_API_KEY=your_key  (free at https://aistudio.google.com/app/apikey)\n"
            "  OPENAI_API_KEY=your_key\n"
            "  ANTHROPIC_API_KEY=your_key"
        )

    provider = config["provider"]
    model = config["model"]

    async with httpx.AsyncClient(timeout=90.0) as client:

        if provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"parts": [{"text": user_message}]}],
            }
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                raise ValueError("Unexpected response structure from Gemini API")

        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEYS", "").split(",")[0]
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": model,
                    "max_tokens": 4096,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_message}],
                },
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"]

        raise ValueError(f"Unknown provider: {provider}")
