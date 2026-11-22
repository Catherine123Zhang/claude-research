"""Non-Anthropic AI platforms, called over their public HTTP APIs.

Each provider returns the answer text plus the web sources it cites.
Response shapes follow each vendor's docs; they are parsed defensively
because vendors change field names over time.

`region` is an ISO country code (e.g. "US", "VN"). Platforms whose API
accepts a user location get it, so answers reflect that market.
"""
from __future__ import annotations

import os

import requests

from .base import Answer, dedupe_citations, urls_in_text

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


class ResponsesProvider:
    """OpenAI Responses API with the web_search tool: ChatGPT, and Grok through xAI's compatible endpoint."""

    PRESETS = {
        "openai": {"url": "https://api.openai.com/v1/responses", "api_key_env": "OPENAI_API_KEY", "model": "gpt-5"},
        "grok": {"url": "https://api.x.ai/v1/responses", "api_key_env": "XAI_API_KEY", "model": "grok-4"},
    }

    def __init__(self, kind: str, model: str | None = None, api_key_env: str | None = None,
                 region: str | None = None):
        preset = self.PRESETS[kind]
        self.url, self.region = preset["url"], region
        self.model = model or preset["model"]
        self.api_key_env = api_key_env or preset["api_key_env"]

    def ask(self, question: str) -> Answer:
        tool = {"type": "web_search"}
        if self.region:
            tool["user_location"] = {"type": "approximate", "country": self.region}
        try:
            data = _post(self.url, {"Authorization": f"Bearer {_key(self.api_key_env)}"},
                         {"model": self.model, "tools": [tool], "input": question})
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
        full = "".join(text)
        return Answer(text=full, citations=dedupe_citations(cites or urls_in_text(full)), queries=queries,
                      model=data.get("model", self.model))


class GeminiProvider:
    """Gemini with Google Search grounding. The API takes no location; the question's language steers it."""

    def __init__(self, model: str = "gemini-2.5-flash", api_key_env: str = "GEMINI_API_KEY", region: str | None = None):
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
    """OpenAI-compatible chat endpoints: Perplexity, Qwen (DashScope), Doubao bots (Ark), Kimi, DeepSeek."""

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
        # Kimi searches through its built-in $web_search tool, which the client must echo back.
        "kimi": {
            "url": "https://api.moonshot.cn/v1/chat/completions",
            "api_key_env": "MOONSHOT_API_KEY",
            "model": "kimi-k2-turbo-preview",
            "extra": {"tools": [{"type": "builtin_function", "function": {"name": "$web_search"}}]},
        },
        # DeepSeek's API has no web search: answers come from model memory only.
        "deepseek": {
            "url": "https://api.deepseek.com/chat/completions",
            "api_key_env": "DEEPSEEK_API_KEY",
            "model": "deepseek-chat",
            "extra": {},
        },
    }

    def __init__(self, kind: str, model: str | None = None, api_key_env: str | None = None, url: str | None = None,
                 region: str | None = None):
        preset = self.PRESETS[kind]
        self.kind = kind
        self.url = url or preset["url"]
        self.model = model or preset["model"]
        self.api_key_env = api_key_env or preset["api_key_env"]
        self.extra = dict(preset["extra"])
        if kind == "perplexity" and region:
            self.extra["web_search_options"] = {"user_location": {"country": region}}

    def ask(self, question: str) -> Answer:
        messages = [{"role": "user", "content": question}]
        try:
            headers = {"Authorization": f"Bearer {_key(self.api_key_env)}"}
            for _ in range(5):
                data = _post(self.url, headers, {"model": self.model, "messages": messages, **self.extra})
                choice = data["choices"][0]
                if choice.get("finish_reason") != "tool_calls":
                    break
                # Kimi's $web_search: hand the arguments straight back and the server runs the search.
                msg = choice["message"]
                messages.append(msg)
                for call in msg.get("tool_calls") or []:
                    messages.append({"role": "tool", "tool_call_id": call["id"], "name": call["function"]["name"],
                                     "content": call["function"]["arguments"]})
            text = choice["message"].get("content") or ""
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
        return Answer(text=text, citations=dedupe_citations(cites or urls_in_text(text)),
                      model=data.get("model", self.model))
