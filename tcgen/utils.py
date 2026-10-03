"""Small helpers (robust JSON extraction from LLM output)."""
from __future__ import annotations

import json
import re


def extract_json(text):
    """Pull the first valid JSON object/array out of an LLM reply (handles ``` fences)."""
    if not isinstance(text, str):  # AIMessage content can be a list of blocks
        text = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in text)
    text = re.sub(r"```(?:json)?", "", text).strip()
    decoder = json.JSONDecoder()
    for m in re.finditer(r"[\[{]", text):
        try:
            obj, _ = decoder.raw_decode(text[m.start():])
            return obj
        except json.JSONDecodeError:
            continue
    raise ValueError("No valid JSON found in model output")
