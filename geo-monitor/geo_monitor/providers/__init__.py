"""Build a provider from one `platforms:` entry in the config."""
from __future__ import annotations

from .base import Answer
from .http_providers import ChatCompletionsProvider, GeminiProvider, OpenAIResponsesProvider


def build_provider(platform: dict):
    kind = platform["type"]
    model = platform.get("model")
    key_env = platform.get("api_key_env")
    if kind == "claude":
        from .claude import ClaudeProvider

        return ClaudeProvider(model=model or "claude-opus-5-5")
    if kind == "openai":
        return OpenAIResponsesProvider(model=model or "gpt-5", api_key_env=key_env or "OPENAI_API_KEY")
    if kind == "gemini":
        return GeminiProvider(model=model or "gemini-2.5-flash", api_key_env=key_env or "GEMINI_API_KEY")
    if kind in ChatCompletionsProvider.PRESETS:
        return ChatCompletionsProvider(kind, model=model, api_key_env=key_env, url=platform.get("url"))
    raise ValueError(f"unknown platform type: {kind}")


__all__ = ["Answer", "build_provider"]
