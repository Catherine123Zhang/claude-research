"""Offline sample answers so the pipeline and dashboard can be tried without API keys.

Every answer it returns is invented. Results are tagged mock=True and the
dashboard labels them as sample data.
"""
from __future__ import annotations

import hashlib
import random

from .base import Answer

SOURCES = {
    "overseas": [
        ("https://www.alibaba.com/showroom/{slug}.html", "{q} - Alibaba.com"),
        ("https://www.made-in-china.com/manufacturers/{slug}.html", "{q} - Made-in-China"),
        ("https://www.globalsources.com/{slug}/", "{q} suppliers - Global Sources"),
        ("https://www.reddit.com/r/smallbusiness/comments/{slug}/", "Anyone sourced this from China?"),
        ("https://www.youtube.com/watch?v={slug}", "Factory tour: how it's made"),
        ("https://www.linkedin.com/pulse/{slug}", "Top OEM suppliers to watch"),
        ("https://www.thomasnet.com/{slug}", "{q} - Thomasnet"),
        ("https://www.statista.com/topics/{slug}/", "Market overview - Statista"),
        ("https://www.quora.com/{slug}", "Which supplier is the best?"),
        ("https://{own}/products/", "Official site"),
    ],
    "domestic": [
        ("https://www.douyin.com/video/{slug}", "{q}｜实测对比"),
        ("https://www.zhihu.com/question/{slug}", "{q}？"),
        ("https://mp.weixin.qq.com/s/{slug}", "{q}，看这一篇就够了"),
        ("https://baijiahao.baidu.com/s?id={slug}", "{q}排行榜"),
        ("https://www.xiaohongshu.com/explore/{slug}", "{q}｜真实体验"),
        ("https://www.1688.com/{slug}.html", "{q} - 1688"),
        ("https://baike.baidu.com/item/{slug}", "{q} - 百度百科"),
        ("https://www.toutiao.com/article/{slug}/", "{q}怎么选"),
        ("https://www.smzdm.com/p/{slug}/", "{q}值得买吗"),
        ("https://{own}/", "品牌官网"),
    ],
}

EXTRA_BRANDS = {"overseas": ["Northwind", "Brightway", "Apex Supply"], "domestic": ["华信", "联创", "优品"]}

TEMPLATE = {
    "overseas": ("Here are some options to consider for: {q}", "{i}. **{b}** - established supplier with export experience and OEM/ODM service.",
                 "Check certifications, MOQ and sample lead time before you order."),
    "domestic": ("关于“{q}”，可以重点看这几家：", "{i}. **{b}**：口碑稳定，产品线齐全，售后有保障。",
                 "建议先对比资质、价格和售后，再根据自己的需求选择。"),
}


class MockProvider:
    def __init__(self, platform_id: str, brands: list[str], sample: int = 0, run_id: str = "",
                 kind: str = "overseas", own_domain: str = "example.com"):
        self.platform_id = platform_id
        self.brands = brands  # display names, first one is the monitored brand
        self.sample = sample
        self.run_id = run_id  # each run gets different sample answers, so trends have something to show
        self.kind = kind if kind in SOURCES else "overseas"
        self.own_domain = own_domain

    def ask(self, question: str) -> Answer:
        seed = hashlib.sha256(f"{self.run_id}|{self.platform_id}|{question}|{self.sample}".encode()).hexdigest()
        rng = random.Random(seed)
        own, others = self.brands[0], self.brands[1:]
        picked = rng.sample(others, k=min(len(others), rng.randint(2, 4)))
        # The monitored brand appears in roughly a third of answers, at a random position.
        if rng.random() < 0.35:
            picked.insert(rng.randint(0, len(picked)), own)
        # Sometimes the AI names a brand nobody configured, which only the judge step catches.
        if rng.random() < 0.4:
            picked.append(rng.choice(EXTRA_BRANDS[self.kind]))
        head, line, tail = TEMPLATE[self.kind]
        lines = [head.format(q=question), ""] + [line.format(i=i, b=b) for i, b in enumerate(picked, 1)] + ["", tail]
        short = question.rstrip("?？")[:24]
        sources = rng.sample(SOURCES[self.kind], k=rng.randint(2, 5))
        cites = [{"url": u.format(slug=seed[:8], own=self.own_domain), "title": t.format(q=short)} for u, t in sources]
        queries = [short, f"{short} {'推荐' if self.kind == 'domestic' else 'supplier'}"][: rng.randint(1, 2)]
        return Answer(text="\n".join(lines), citations=cites, queries=queries, model=f"mock-{self.platform_id}")

    def judge(self, answer_text: str) -> dict:
        """Stand-in for the LLM judge: brands in order of appearance, sentiment toward the monitored brand."""
        rng = random.Random(hashlib.sha256(answer_text.encode()).hexdigest())
        candidates = self.brands + EXTRA_BRANDS[self.kind]
        names = [b for _, b in sorted((answer_text.find(b), b) for b in candidates if b in answer_text)]
        own = self.brands[0]
        sentiment = rng.choices(["正面", "中性", "负面"], weights=[6, 3, 1])[0] if own in names else "未提及"
        return {"all_brands": names, "sentiment": sentiment}
