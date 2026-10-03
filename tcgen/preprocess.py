"""Module 1/2: input handling, cleaning, normalisation and story parsing."""
from __future__ import annotations

import json
import re

MIN_LEN, MAX_LEN = 10, 3000

_STORY_RE = re.compile(
    r"as\s+(?:an?|the)\s+(?P<actor>.+?),?\s+i\s+(?:want|need|would like|wish)(?:\s+to)?\s+"
    r"(?P<goal>.+?)(?:,?\s+(?:so that|in order to)\s+(?P<benefit>.+?))?\.?\s*$",
    re.IGNORECASE | re.DOTALL,
)

VAGUE_WORDS = [
    "somehow", "etc", "and so on", "properly", "appropriate", "appropriately", "as needed",
    "user-friendly", "user friendly", "better", "good", "fast", "flexible", "easy", "nice",
]


def clean_text(text: str) -> str:
    """Normalise whitespace and typographic quotes."""
    text = (text or "").replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", " ", text)
    return text.strip()


def validate_story(text: str) -> str:
    if not text or len(text) < MIN_LEN:
        raise ValueError(f"User story is too short (minimum {MIN_LEN} characters).")
    if len(text) > MAX_LEN:
        raise ValueError(f"User story is too long (maximum {MAX_LEN} characters).")
    return text


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def parse_story_template(text: str) -> dict:
    """Extract actor / goal / benefit from 'As a X, I want Y so that Z' stories."""
    m = _STORY_RE.match(clean_text(text))
    if not m:
        return {"actor": "", "goal": "", "benefit": "", "structured": False}
    return {
        "actor": (m.group("actor") or "").strip(" ,."),
        "goal": (m.group("goal") or "").strip(" ,."),
        "benefit": (m.group("benefit") or "").strip(" ,."),
        "structured": True,
    }


def vague_terms(text: str) -> list[str]:
    low = text.lower()
    return [w for w in VAGUE_WORDS if re.search(rf"\b{re.escape(w)}\b", low)]


def load_stories(filename: str, content) -> list[str]:
    """Load stories from .txt (blank-line or line separated) or .json."""
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="ignore")
    if filename.lower().endswith(".json"):
        data = json.loads(content)
        if isinstance(data, dict):
            data = data.get("user_stories") or [data.get("user_story", "")]
        stories = []
        for item in data:
            stories.append(item.get("user_story", "") if isinstance(item, dict) else str(item))
    else:
        blocks = [b for b in re.split(r"\n\s*\n", content) if b.strip()]
        stories = blocks if len(blocks) > 1 else [l for l in content.splitlines() if l.strip()]
    return [clean_text(s) for s in stories if clean_text(s)]
