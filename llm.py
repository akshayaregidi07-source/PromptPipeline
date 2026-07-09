"""
╔══════════════════════════════════════════════════════════════════╗
║  LLM — Language Model Interface                                 ║
║  Handles API calls to OpenRouter with error handling & timing   ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import time
import json
import requests
from typing import Optional

# ─── Default Models ──────────────────────────────────────────
DEFAULT_MODEL = "google/gemini-2.5-flash-lite"
REASON_MODEL = "google/gemini-2.5-flash"
FALLBACK_MODEL = "openai/gpt-4o-mini"

# ─── API Timeout ─────────────────────────────────────────────
TIMEOUT = 90


def call_llm(
    prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.1,
    api_key: Optional[str] = None,
) -> dict:
    """
    Call the LLM via OpenRouter.

    Returns:
        {
            "success": bool,
            "text": str,           # Raw response text (if success)
            "model": str,          # Model used
            "latency": float,      # Seconds
            "tokens": int | None,  # Total tokens (if reported)
            "error": str | None,   # Error message (if failed)
        }
    """
    key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        return {
            "success": False,
            "text": "",
            "model": model,
            "latency": 0,
            "tokens": None,
            "error": "No API key provided. Set OPENROUTER_API_KEY env var or pass api_key.",
        }

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://prompt-pipeline.app",
        "X-Title": "Prompt Pipeline",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": 4096,
    }

    start = time.time()
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
        latency = round(time.time() - start, 2)

        if resp.status_code == 401:
            return {
                "success": False,
                "text": "",
                "model": model,
                "latency": latency,
                "tokens": None,
                "error": "Invalid API key. Check your OpenRouter key.",
            }
        if resp.status_code == 429:
            return {
                "success": False,
                "text": "",
                "model": model,
                "latency": latency,
                "tokens": None,
                "error": "Rate limited (429). Try again in a few seconds.",
            }

        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"].strip()
        tokens = data.get("usage", {}).get("total_tokens", None)

        return {
            "success": True,
            "text": text,
            "model": data.get("model", model),
            "latency": latency,
            "tokens": tokens,
            "error": None,
        }

    except requests.exceptions.Timeout:
        latency = round(time.time() - start, 2)
        return {
            "success": False,
            "text": "",
            "model": model,
            "latency": latency,
            "tokens": None,
            "error": f"Request timed out after {TIMEOUT}s.",
        }
    except requests.exceptions.ConnectionError:
        latency = round(time.time() - start, 2)
        return {
            "success": False,
            "text": "",
            "model": model,
            "latency": latency,
            "tokens": None,
            "error": "Network error. Check your internet connection.",
        }
    except Exception as e:
        latency = round(time.time() - start, 2)
        return {
            "success": False,
            "text": "",
            "model": model,
            "latency": latency,
            "tokens": None,
            "error": str(e),
        }