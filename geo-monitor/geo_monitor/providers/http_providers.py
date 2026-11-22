"""Non-Anthropic AI platforms, called over their public HTTP APIs.

Each provider returns the answer text plus the web sources it cites.
Response shapes follow each vendor's docs; they are parsed defensively
because vendors change field names over time.
"""
from __future__ import annotations

import os

import requests

from .base import Answer, dedupe_citations

TIMEOUT = 180


def _key(env: str) -> str:
    value = os.environ.get(env, "")
    if not value:
        raise RuntimeError(f"environment variable {env} is not set")
    return value


def _post(url: str, headers: dict, body: dict) -> dict:
    r = requests.post(url, headers=headers, json=body, timeout=TIMEOUT)
    if r.status_code >= 400:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


class OpenAIResponsesProvider:
    """ChatGPT via the OpenAI Responses API with the web_search tool."""

    def __init__(self, model: str = "gpt-5", api_key_env: str = "OPENAI_API_KEY"):
        self.model, self.api_key_env = model, api_key_env

    def ask(self, question: str) -> Answer:
        try:
            data = _post(
                "https://api.openai.com/v1/responses",
                {"Authorization": f"Bearer {_key(self.api_key_env)}"},
                {"model": self.model, "tools": [{"type": "web_search"}], "input": question},
            )
        except Exception as e:  # noqa: BLE001 - report any failure as a row error
            return Answer(model=self.model, error=str(e))
        text, cites, queries = [], [], []
        for item in data.get("output", []):
            if item.get("type") == "web_search_call":
                q = (item.get("action") or {}).get("query")
                if q:
                    queries.append(q)
            if item.get("type") != "message":
                continue
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    text.append(part.get("text", ""))
                    for a in part.get("annotations", []):
                        if a.get("type") == "url_citation":
                            cites.append({"url": a.get("url"), "title": a.get("title")})
        return Answer(text="".join(text), citations=dedupe_citations(cites), queries=queries,
                      model=data.get("model", self.model))


class GeminiProvider:
    """Gemini with Google Search grounding."""

    def __init__(self, model: str = "gemini-2.5-flash", api_key_env: str = "GEMINI_API_KEY"):
        self.model, self.api_key_env = model, api_key_env

    def ask(self, question: str) -> Answer:
        try:
            data = _post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                {"x-goog-api-key": _key(self.api_key_env)},
                {"contents": [{"parts": [{"text": question}]}], "tools": [{"google_search": {}}]},
            )
            cand = data["candidates"][0]
        except Exception as e:  # noqa: BLE001
            return Answer(model=self.model, error=str(e))
        text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
        cites = []
        for chunk in cand.get("groundingMetadata", {}).get("groundingChunks", []):
            web = chunk.get("web", {})
            # Gemini returns redirect URLs; the title holds the source domain.
            cites.append({"url": web.get("uri", ""), "title": web.get("title", "")})
        queries = cand.get("groundingMetadata", {}).get("webSearchQueries", [])
        return Answer(text=text, citations=dedupe_citations(cites), queries=queries, model=self.model)


class ChatCompletionsProvider:
    """OpenAI-compatible chat endpoints: Perplexity, Qwen (DashScope), Doubao bots (Ark), DeepSeek."""

    PRESETS = {
        "perplexity": {
            "url": "https://api.perplexity.ai/chat/completions",
            "api_key_env": "PERPLEXITY_API_KEY",
            "model": "sonar",
            "extra": {},
        },
        "qwen": {
            "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            "api_key_env": "DASHSCOPE_API_KEY",
            "model": "qwen-plus",
            "extra": {"enable_search": True, "search_options": {"forced_search": True, "enable_source": True}},
        },
        # Doubao web search runs through an Ark "bot" (应用) with the 联网 plugin; model = the bot id.
        "doubao_bot": {
            "url": "https://ark.cn-beijing.volces.com/api/v3/bots/chat/completions",
            "api_key_env": "ARK_API_KEY",
            "model": "bot-xxxxxxxx",
            "extra": {},
        },
        # DeepSeek's API has no web search: answers come from model memory only.
        "deepseek": {
            "url": "https://api.deepseek.com/chat/completions",
            "api_key_env": "DEEPSEEK_API_KEY",
            "model": "deepseek-chat",
            "extra": {},
        },
    }

    def __init__(self, kind: str, model: str | None = None, api_key_env: str | None = None, url: str | None = None):
        preset = self.PRESETS[kind]
        self.kind = kind
        self.url = url or preset["url"]
        self.model = model or preset["model"]
        self.api_key_env = api_key_env or preset["api_key_env"]
        self.extra = preset["extra"]

    def ask(self, question: str) -> Answer:
        body = {"model": self.model, "messages": [{"role": "user", "content": question}], **self.extra}
        try:
            data = _post(self.url, {"Authorization": f"Bearer {_key(self.api_key_env)}"}, body)
            text = data["choices"][0]["message"].get("content") or ""
        except Exception as e:  # noqa: BLE001
            return Answer(model=self.model, error=str(e))
        cites: list[dict] = []
        for r in data.get("search_results") or []:  # Perplexity
            cites.append({"url": r.get("url"), "title": r.get("title")})
        for url in data.get("citations") or []:  # Perplexity, older shape
            if isinstance(url, str):
                cites.append({"url": url, "title": ""})
        for r in (data.get("search_info") or {}).get("search_results") or []:  # Qwen
            cites.append({"url": r.get("url"), "title": r.get("title") or r.get("site_name")})
        for r in data.get("references") or []:  # Doubao bot
            cites.append({"url": r.get("url"), "title": r.get("title") or r.get("site_name")})
        return Answer(text=text, citations=dedupe_citations(cites), model=data.get("model", self.model))
