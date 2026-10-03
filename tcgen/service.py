"""Glue used by the Streamlit UI, FastAPI app and CLI."""
from __future__ import annotations

from functools import lru_cache

from . import db
from .agent import CaseGenerationAgent, Components
from .config import Settings, get_settings


@lru_cache(maxsize=1)
def get_settings_cached() -> Settings:
    return get_settings()


@lru_cache(maxsize=1)
def get_components() -> Components:
    return Components.build(get_settings_cached())


def run_generation(story: str, persist: bool = True) -> dict:
    settings = get_settings_cached()
    agent = CaseGenerationAgent(settings, get_components())  # fresh agent/state per run, shared models
    result = agent.run(story)
    if persist:
        result["story_id"] = db.save_run(settings.db_path, result)
    return result
