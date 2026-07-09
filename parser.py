"""
╔══════════════════════════════════════════════════════════════════╗
║  Parser — JSON Extraction & Validation with Auto-Retry          ║
║  Extracts JSON from LLM responses, validates, retries on fail   ║
╚══════════════════════════════════════════════════════════════════╝
"""

import re
import json
from typing import Any, Optional

from llm import call_llm

MAX_RETRIES = 3

REPAIR_PROMPT = """You returned invalid JSON. The previous output was:

{raw_output}

It could not be parsed. Return ONLY valid JSON matching the expected schema. No markdown fences. No explanation. No extra text. Just the JSON object."""


def extract_json_block(text: str) -> Optional[str]:
    """Extract JSON from markdown code blocks or raw text."""
    # Try ```json ... ``` blocks first
    block_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if block_match:
        candidate = block_match.group(1).strip()
        # Verify it looks like JSON
        if candidate.startswith(("{", "[")):
            return candidate

    # Try ``` ... ``` without language specifier
    block_match = re.search(r"```\s*([\s\S]*?)```", text)
    if block_match:
        candidate = block_match.group(1).strip()
        if candidate.startswith(("{", "[")):
            return candidate

    # Try raw text
    text_stripped = text.strip()
    if text_stripped.startswith(("{", "[")):
        return text_stripped

    # Try to find JSON-like content between { } or [ ]
    for delim_open, delim_close in [("{", "}"), ("[", "]")]:
        start = text.find(delim_open)
        if start != -1:
            # Find matching closing delimiter
            depth = 0
            for i in range(start, len(text)):
                if text[i] == delim_open:
                    depth += 1
                elif text[i] == delim_close:
                    depth -= 1
                    if depth == 0:
                        return text[start : i + 1]

    return None


def parse_json(
    raw: str,
    retries: int = MAX_RETRIES,
    repair_fn=None,
) -> dict:
    """
    Parse JSON from LLM output with automatic retry on failure.

    Args:
        raw: Raw text from LLM
        retries: Max retry attempts
        repair_fn: Function to call for repair (call_llm wrapper)

    Returns:
        Parsed dict, or dict with _parse_error=True on failure
    """
    attempts = []
    current_raw = raw

    for attempt in range(1, retries + 1):
        # Extract JSON block
        json_str = extract_json_block(current_raw)

        if json_str:
            try:
                result = json.loads(json_str)
                return {
                    "success": True,
                    "data": result,
                    "attempts": attempts,
                    "retries": attempt - 1,
                }
            except json.JSONDecodeError as e:
                attempts.append(
                    {
                        "attempt": attempt,
                        "error": f"JSONDecodeError: {e}",
                        "preview": current_raw[:200],
                    }
                )
        else:
            attempts.append(
                {
                    "attempt": attempt,
                    "error": "No JSON block found in response",
                    "preview": current_raw[:200],
                }
            )

        # Try repair if we have more retries
        if attempt < retries:
            repair_text = REPAIR_PROMPT.format(raw_output=current_raw)
            if repair_fn:
                repair_result = repair_fn(repair_text)
            else:
                repair_result = call_llm(repair_text, temperature=0.0)

            if repair_result.get("success"):
                current_raw = repair_result["text"]
            else:
                attempts.append(
                    {
                        "attempt": attempt + 1,
                        "error": f"Repair call failed: {repair_result.get('error')}",
                        "preview": "",
                    }
                )
                break

    return {
        "success": False,
        "data": None,
        "attempts": attempts,
        "retries": retries,
        "error": f"Failed to parse JSON after {retries} retries",
    }