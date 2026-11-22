"""Common types for AI platform providers."""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Answer:
    """One AI answer to one question."""

    text: str = ""
    # Sources the answer cites: [{"url": ..., "title": ...}]
    citations: list[dict] = field(default_factory=list)
    # Search keywords the AI itself typed into its web search, when the platform exposes them.
    queries: list[str] = field(default_factory=list)
    model: str = ""
    error: str | None = None


def dedupe_citations(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        url = (item.get("url") or "").strip()
        key = url or (item.get("title") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append({"url": url, "title": (item.get("title") or "").strip()})
    return out


URL_RE = re.compile(r"https?://[^\s)\]>\"'，。、]+")


def urls_in_text(text: str) -> list[dict]:
    """Links written into the answer itself, for platforms that return no structured citations."""
    return [{"url": u.rstrip(".,;:"), "title": ""} for u in URL_RE.findall(text or "")]
