"""LLM factory. Returns (chat_model | None, status). None => offline template mode."""
from __future__ import annotations

from .config import DEFAULT_MODELS, Settings


def get_llm(settings: Settings):
    provider = (settings.llm_provider or "none").lower()
    if provider in {"", "none", "offline"}:
        return None, "offline-template (no LLM configured)"
    model = settings.llm_model or DEFAULT_MODELS.get(provider, "")
    try:
        if provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(model=model, temperature=settings.temperature)
        elif provider == "openai":
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model=model, temperature=settings.temperature)
        elif provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(model=model, temperature=settings.temperature, max_tokens=4096)
        elif provider == "ollama":
            from langchain_ollama import ChatOllama
            llm = ChatOllama(model=model, temperature=settings.temperature)
        else:
            return None, f"offline-template (unknown LLM_PROVIDER '{provider}')"
        return llm, f"{provider}:{model}"
    except Exception as exc:  # missing package / missing API key
        return None, f"offline-template (LLM init failed: {exc})"
