"""Claude with the server-side web search tool (Anthropic Python SDK)."""
from __future__ import annotations

import anthropic

from .base import Answer, dedupe_citations

MAX_CONTINUATIONS = 5


class ClaudeProvider:
    def __init__(self, model: str = "claude-opus-5-5", max_searches: int = 5, region: str | None = None):
        self.model = model
        self.max_searches = max_searches
        self.region = region
        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY or an `ant auth login` profile

    def ask(self, question: str) -> Answer:
        search = {"type": "web_search_20260209", "name": "web_search", "max_uses": self.max_searches}
        if self.region:
            search["user_location"] = {"type": "approximate", "country": self.region}
        tools = [search]
        messages = [{"role": "user", "content": question}]
        try:
            for _ in range(MAX_CONTINUATIONS):
                response = self.client.beta.messages.create(
                    model=self.model,
                    max_tokens=16000,
                    betas=["server-side-fallback-2026-07-01"],
                    fallbacks="default",
                    tools=tools,
                    messages=messages,
                )
                if response.stop_reason != "pause_turn":
                    break
                # Long search turns pause; send the turn back and the server resumes it.
                messages = [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": response.content},
                ]
        except anthropic.RateLimitError as e:
            return Answer(model=self.model, error=f"rate limited: {e}")
        except anthropic.APIStatusError as e:
            return Answer(model=self.model, error=f"API error {e.status_code}: {e.message}")
        except anthropic.APIConnectionError as e:
            return Answer(model=self.model, error=f"connection error: {e}")

        if response.stop_reason == "refusal":
            category = response.stop_details.category if response.stop_details else None
            return Answer(model=response.model, error=f"refused ({category})")

        text_parts: list[str] = []
        cited: list[dict] = []
        searched: list[dict] = []
        queries: list[str] = []
        for block in response.content:
            if block.type == "server_tool_use" and block.name == "web_search":
                q = (block.input or {}).get("query")
                if q:
                    queries.append(q)
            elif block.type == "text":
                text_parts.append(block.text)
                for c in getattr(block, "citations", None) or []:
                    if getattr(c, "type", "") == "web_search_result_location":
                        cited.append({"url": c.url, "title": c.title})
            elif block.type == "web_search_tool_result" and isinstance(block.content, list):
                for r in block.content:
                    searched.append({"url": r.url, "title": r.title})

        return Answer(
            text="".join(text_parts),
            citations=dedupe_citations(cited or searched),
            queries=queries,
            model=response.model,
        )
