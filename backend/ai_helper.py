"""
ai_helper.py
============
Robust AI utility module.
Supports Google Gemini (preferred free tier), Anthropic Claude, and OpenAI ChatGPT.
Automatically detects which provider to use based on the .env file.
"""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

# Detect Provider based on available API Keys
def get_runtime_ai_config() -> dict:
    if os.getenv("GEMINI_API_KEY"):
        return {"provider": "gemini", "api_key_configured": True, "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), "configured_key_count": 1}
    elif os.getenv("OPENAI_API_KEY"):
        return {"provider": "openai", "api_key_configured": True, "model": os.getenv("OPENAI_MODEL", "gpt-4o"), "configured_key_count": 1}
    elif os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEYS"):
        keys = os.getenv("ANTHROPIC_API_KEYS", "")
        count = len(keys.split(",")) if keys else 1
        return {"provider": "anthropic", "api_key_configured": True, "model": os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307"), "configured_key_count": count}
    
    return {"provider": "none", "api_key_configured": False, "model": "None", "configured_key_count": 0}

async def call_ai(system_prompt: str, user_message: str) -> str:
    """
    Unified method to call any AI provider.
    """
    config = get_runtime_ai_config()
    
    if not config["api_key_configured"]:
        raise ValueError(
            "No API Key found! Please create a .env file inside backend/ and add ONE of the following:\n"
            "GEMINI_API_KEY=your_key_here (Recommended, Free!)\n"
            "OPENAI_API_KEY=your_key_here\n"
            "ANTHROPIC_API_KEY=your_key_here\n"
            "Get a free Gemini key here: https://aistudio.google.com/app/apikey"
        )

    provider = config["provider"]
    model = config["model"]

    async with httpx.AsyncClient(timeout=90.0, verify=False) as client:

        if provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "systemInstruction": { "parts": [{ "text": system_prompt }] },
                "contents": [{ "parts": [{ "text": user_message }] }],
            }
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                 raise ValueError("Unexpected response from Gemini API")

        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            }
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEYS").split(",")[0]
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": user_message}
                ]
            }
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]

# Temporary alias to prevent ImportError in Week 2/3/4 files
call_claude = call_ai
