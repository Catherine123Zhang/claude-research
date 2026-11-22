"""Turn a raw answer into the numbers the dashboard shows."""
from __future__ import annotations

import re
from urllib.parse import urlparse


SITE_TYPES = {
    "视频平台": ["youtube.com", "douyin.com", "bilibili.com", "tiktok.com", "ixigua.com", "vimeo.com"],
    "问答/论坛": ["zhihu.com", "quora.com", "reddit.com", "tieba.baidu.com", "stackexchange.com"],
    "B2B 平台": ["alibaba.com", "made-in-china.com", "globalsources.com", "thomasnet.com", "1688.com", "tradekey.com", "ec21.com"],
    "电商平台": ["amazon.com", "jd.com", "tmall.com", "taobao.com", "ebay.com", "walmart.com"],
    "社交媒体": ["linkedin.com", "facebook.com", "instagram.com", "x.com", "twitter.com", "xiaohongshu.com", "weibo.com"],
    "自媒体/公众号": ["mp.weixin.qq.com", "baijiahao.baidu.com", "toutiao.com", "sohu.com", "163.com", "medium.com"],
    "百科": ["baike.baidu.com", "wikipedia.org", "baike.sogou.com"],
    "数据/研究": ["statista.com", "grandviewresearch.com", "mordorintelligence.com"],
}


SITE_NAMES = {
    "youtube.com": "YouTube", "douyin.com": "抖音", "bilibili.com": "哔哩哔哩", "tiktok.com": "TikTok",
    "zhihu.com": "知乎", "quora.com": "Quora", "reddit.com": "Reddit", "tieba.baidu.com": "百度贴吧",
    "alibaba.com": "阿里巴巴国际站", "made-in-china.com": "中国制造网", "globalsources.com": "环球资源",
    "thomasnet.com": "Thomasnet", "1688.com": "1688", "tradekey.com": "TradeKey",
    "amazon.com": "Amazon", "jd.com": "京东", "tmall.com": "天猫", "taobao.com": "淘宝",
    "linkedin.com": "LinkedIn", "facebook.com": "Facebook", "instagram.com": "Instagram", "x.com": "X",
    "xiaohongshu.com": "小红书", "weibo.com": "微博", "mp.weixin.qq.com": "微信公众号",
    "baijiahao.baidu.com": "百家号", "toutiao.com": "今日头条", "sohu.com": "搜狐", "163.com": "网易",
    "sina.com.cn": "新浪", "medium.com": "Medium", "baike.baidu.com": "百度百科", "wikipedia.org": "维基百科",
    "statista.com": "Statista", "smzdm.com": "什么值得买",
}


def site_name(domain: str) -> str:
    for root, name in SITE_NAMES.items():
        if domain == root or domain.endswith("." + root):
            return name
    return domain


def site_type(domain: str, own_domains: list[str]) -> str:
    if any(domain == d or domain.endswith("." + d) for d in own_domains):
        return "品牌官网"
    for label, roots in SITE_TYPES.items():
        if any(domain == r or domain.endswith("." + r) for r in roots):
            return label
    return "其他网站"


def domain_of(citation: dict) -> str:
    url = citation.get("url") or ""
    host = urlparse(url).netloc.lower()
    # Gemini cites through vertexaisearch redirect links; its title carries the real domain.
    if not host or "vertexaisearch" in host:
        host = (citation.get("title") or "").lower()
    return host.removeprefix("www.")


def _first_and_count(text: str, aliases: list[str]) -> tuple[int, int]:
    first, count = -1, 0
    for alias in aliases:
        # Word boundaries for Latin names so "Oral" does not match "Oral-B" twice; plain match for CJK.
        pattern = re.escape(alias)
        if re.fullmatch(r"[\w .&'-]+", alias, flags=re.ASCII):
            pattern = rf"(?<![A-Za-z0-9]){pattern}(?![A-Za-z0-9])"
        hits = [m.start() for m in re.finditer(pattern, text, flags=re.IGNORECASE)]
        if hits:
            count += len(hits)
            first = hits[0] if first < 0 else min(first, hits[0])
    return first, count


def analyze(text: str, citations: list[dict], brands: list[dict]) -> dict:
    """brands: [{"name", "aliases", "domains", "own": bool}]. Returns per-brand mention data."""
    domains = [domain_of(c) for c in citations]
    found = []
    for b in brands:
        aliases = b.get("aliases") or [b["name"]]
        first, count = _first_and_count(text, aliases)
        own_domains = [d.lower().removeprefix("www.") for d in b.get("domains", [])]
        site_cited = any(d == od or d.endswith("." + od) for d in domains for od in own_domains)
        found.append({"name": b["name"], "own": b.get("own", False), "first": first,
                      "count": count, "site_cited": site_cited})
    own_domains = [d.lower().removeprefix("www.") for b in brands if b.get("own") for d in b.get("domains", [])]
    mentioned = sorted((f for f in found if f["count"] > 0), key=lambda f: f["first"])
    rank = {f["name"]: i + 1 for i, f in enumerate(mentioned)}
    return {
        "brands": [
            {"name": f["name"], "own": f["own"], "mentioned": f["count"] > 0, "count": f["count"],
             "rank": rank.get(f["name"]), "site_cited": f["site_cited"]}
            for f in found
        ],
        "domains": domains,
        "site_types": [site_type(d, own_domains) for d in domains],
    }
