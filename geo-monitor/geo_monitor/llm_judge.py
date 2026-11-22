"""Read an AI answer with Claude: every brand it names, and its tone toward the monitored brand.

Keyword matching only finds brands you listed in the config. This step also
finds brands you did not think to track (爱搜's "AI对话提及全部品牌").
"""
from __future__ import annotations

from typing import Literal

import anthropic
from pydantic import BaseModel, Field


class Judgement(BaseModel):
    all_brands: list[str] = Field(description="Every brand, company or manufacturer the answer names, in order of first appearance, deduplicated.")
    sentiment: Literal["正面", "中性", "负面", "未提及"] = Field(description="Tone toward the monitored brand; 未提及 if the answer does not name it.")


PROMPT = """Below is an answer an AI assistant gave to a user's question.

Question: {question}
Monitored brand: {brand} (also written as: {aliases})

Answer:
<answer>
{answer}
</answer>

List every brand, company or manufacturer the answer names, in the order they first appear. Use the name as written in the answer; merge spellings of the same brand. Leave out platforms that are only cited as sources (such as Alibaba.com or Reddit) unless the answer recommends them as a supplier.
Then rate the answer's tone toward the monitored brand: 正面 if it is recommended or described favourably, 负面 if it is criticised or warned against, 中性 if it is only listed, 未提及 if it does not appear."""


class LLMJudge:
    def __init__(self, model: str = "claude-opus-5-5"):
        self.model = model
        self.client = anthropic.Anthropic()

    def judge(self, question: str, answer: str, brand: str, aliases: list[str]) -> dict:
        try:
            response = self.client.beta.messages.parse(
                model=self.model,
                max_tokens=4000,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                output_config={"effort": "low"},
                output_format=Judgement,
                messages=[{"role": "user", "content": PROMPT.format(
                    question=question, brand=brand, aliases=", ".join(aliases), answer=answer)}],
            )
        except anthropic.APIStatusError as e:
            return {"error": f"judge API error {e.status_code}: {e.message}"}
        except anthropic.APIConnectionError as e:
            return {"error": f"judge connection error: {e}"}
        if response.stop_reason == "refusal" or response.parsed_output is None:
            return {"error": f"judge returned no result ({response.stop_reason})"}
        return response.parsed_output.model_dump()
