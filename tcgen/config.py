"""Central configuration, read from environment variables / .env."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional at import time
    load_dotenv = None

ROOT = Path(__file__).resolve().parent.parent
if load_dotenv:
    load_dotenv(ROOT / ".env")

DEFAULT_MODELS = {
    "google": "gemini-2.0-flash",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-5",
    "ollama": "llama3.1",
}

# Thresholds depend on the embedding backend. TF-IDF: duplicate = cosine, coverage/relevance =
# term containment (share of a requirement's terms found in the test case). Dense: cosine for all.
THRESHOLDS = {
    "tfidf": {"duplicate": 0.85, "coverage": 0.40, "relevance": 0.40},
    "dense": {"duplicate": 0.90, "coverage": 0.45, "relevance": 0.35},
}


def _bool(value, default: bool) -> bool:
    if value is None or value == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass
class Settings:
    llm_provider: str = "none"
    llm_model: str = ""
    temperature: float = 0.2
    embedding_backend: str = "tfidf"
    max_refinements: int = 2
    use_llm_planner: bool = True
    target_percent: float = 80.0          # success metric: coverage and relevance >= 80%
    min_cases: int = 6
    models_dir: Path = field(default_factory=lambda: ROOT / "models")
    db_path: Path = field(default_factory=lambda: ROOT / "data" / "testcases.db")

    @property
    def thresholds(self) -> dict:
        return THRESHOLDS["tfidf" if self.embedding_backend == "tfidf" else "dense"]

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "none").strip().lower(),
            llm_model=os.getenv("LLM_MODEL", "").strip(),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.2") or 0.2),
            embedding_backend=os.getenv("EMBEDDING_BACKEND", "tfidf").strip().lower(),
            max_refinements=int(os.getenv("MAX_REFINEMENTS", "2") or 2),
            use_llm_planner=_bool(os.getenv("USE_LLM_PLANNER"), True),
        )


def get_settings() -> Settings:
    return Settings.from_env()
