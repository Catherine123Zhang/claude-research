"""Offline sample answers so the pipeline and dashboard can be tried without API keys.

Every answer it returns is invented. Results are tagged mock=True and the
dashboard labels them as sample data.
"""
from __future__ import annotations

import hashlib
import random

from .base import Answer

SOURCE_POOL = [
    ("https://www.alibaba.com/showroom/electric-toothbrush-oem.html", "Electric Toothbrush OEM - Alibaba.com"),
    ("https://www.made-in-china.com/manufacturers/sonic-toothbrush.html", "Sonic Toothbrush Manufacturers - Made-in-China"),
    ("https://www.globalsources.com/electric-toothbrush/", "Electric toothbrush suppliers - Global Sources"),
    ("https://www.reddit.com/r/AskElectronics/comments/oem_toothbrush/", "Anyone sourced electric toothbrushes from China?"),
    ("https://www.youtube.com/watch?v=factorytour", "Inside a Chinese toothbrush factory"),
    ("https://www.linkedin.com/pulse/top-oral-care-oem-suppliers", "Top oral care OEM suppliers"),
    ("https://www.cnjideng.com/products/", "JIDENG Sonic Toothbrush"),
    ("https://www.statista.com/topics/oral-care/", "Oral care market - Statista"),
    ("https://www.thomasnet.com/oral-care-suppliers", "Oral care suppliers - Thomasnet"),
    ("https://www.zhihu.com/question/oem-toothbrush", "电动牙刷代工厂哪家好？"),
]


QUERY_POOL = [
    "electric toothbrush OEM manufacturer China",
    "sonic toothbrush factory private label",
    "best electric toothbrush supplier MOQ",
    "oral care OEM ISO13485 China",
    "电动牙刷 代工厂 推荐",
]

EXTRA_BRANDS = ["Xiaomi", "Usmile", "Seago", "Lebooo"]


class MockProvider:
    def __init__(self, platform_id: str, brands: list[str], sample: int = 0):
        self.platform_id = platform_id
        self.brands = brands  # display names, first one is the monitored brand
        self.sample = sample

    def ask(self, question: str) -> Answer:
        seed = hashlib.sha256(f"{self.platform_id}|{question}|{self.sample}".encode()).hexdigest()
        rng = random.Random(seed)
        own, others = self.brands[0], self.brands[1:]
        picked = rng.sample(others, k=min(len(others), rng.randint(2, 4)))
        # The monitored brand appears in roughly a third of answers, at a random position.
        if rng.random() < 0.35:
            picked.insert(rng.randint(0, len(picked)), own)
        # Sometimes the AI names a brand nobody configured, which only the judge step catches.
        if rng.random() < 0.4:
            picked.append(rng.choice(EXTRA_BRANDS))
        lines = [f"Here are some options to consider for: {question}", ""]
        for i, name in enumerate(picked, 1):
            lines.append(f"{i}. **{name}** - established supplier with export experience and OEM/ODM service.")
        lines += ["", "Check certifications (CE, FCC, FDA), MOQ and sample lead time before you order."]
        sources = rng.sample(SOURCE_POOL, k=rng.randint(2, 5))
        queries = rng.sample(QUERY_POOL, k=rng.randint(1, 3))
        return Answer(
            text="\n".join(lines),
            citations=[{"url": u, "title": t} for u, t in sources],
            queries=queries,
            model=f"mock-{self.platform_id}",
        )

    def judge(self, answer_text: str) -> dict:
        """Stand-in for the LLM judge: brands in order of appearance, sentiment toward the monitored brand."""
        rng = random.Random(hashlib.sha256(answer_text.encode()).hexdigest())
        candidates = self.brands + EXTRA_BRANDS
        names = [b for _, b in sorted((answer_text.find(b), b) for b in candidates if b in answer_text)]
        own = self.brands[0]
        sentiment = rng.choices(["正面", "中性", "负面"], weights=[6, 3, 1])[0] if own in names else "未提及"
        return {"all_brands": names, "sentiment": sentiment}
