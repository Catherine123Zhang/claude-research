"""Per-platform statistics and brand tiers, shared by the report and the diagnosis step."""
from __future__ import annotations

from collections import Counter


def canonical(name: str, tracked: list[dict]) -> str:
    n = name.lower()
    for b in tracked:
        aliases = [b["name"].lower(), *(a.lower() for a in b.get("aliases", []))]
        if any(n == a or a in n or n in a for a in aliases):
            return b["name"]
    return name


def brand_hits(rec: dict, tracked: list[dict]) -> dict[str, int]:
    """Brand name -> rank in this answer. Uses the judge's full brand list when present."""
    hits: dict[str, int] = {}
    judged = (rec.get("judge") or {}).get("all_brands")
    if judged:
        for name in judged:
            c = canonical(name, tracked)
            hits.setdefault(c, len(hits) + 1)
    else:
        for b in rec["analysis"]["brands"]:
            if b["mentioned"]:
                hits[b["name"]] = b["rank"]
    return hits


def tier_of(score: float, top: float) -> str:
    """T1/T2/T3 relative to the strongest brand on the same platform."""
    if top <= 0 or score <= 0:
        return "—"
    ratio = score / top
    return "T1" if ratio >= 0.66 else "T2" if ratio >= 0.33 else "T3"


def platform_stats(records: list[dict], tracked: list[dict], platforms: list[dict]) -> dict:
    own_name = next(b["name"] for b in tracked if b.get("own"))
    out = {}
    for p in platforms:
        recs = [r for r in records if r["platform"] == p["id"] and not r.get("error")]
        if not recs:
            continue
        counts, rank_sum = Counter(), Counter()
        for r in recs:
            for name, rank in brand_hits(r, tracked).items():
                counts[name] += 1
                rank_sum[name] += rank
        brands = []
        for name, n in counts.items():
            rate = n / len(recs)
            avg_rank = rank_sum[name] / n
            # Being named often matters most; being named first adds weight.
            score = rate / (1 + 0.25 * (avg_rank - 1))
            brands.append({"name": name, "own": name == own_name, "rate": round(rate, 3),
                           "avg_rank": round(avg_rank, 2), "score": score})
        top = max((b["score"] for b in brands), default=0)
        for b in brands:
            b["tier"] = tier_of(b["score"], top)
            b["score"] = round(b["score"], 3)
        brands.sort(key=lambda b: -b["score"])
        domains = Counter(d for r in recs for d in set(r["analysis"]["domains"]) if d)
        types = Counter(t for r in recs for t in r["analysis"].get("site_types", []))
        sentiment = Counter((r.get("judge") or {}).get("sentiment") for r in recs
                            if (r.get("judge") or {}).get("sentiment") not in (None, "未提及"))
        own = next((b for b in brands if b["own"]), None)
        out[p["id"]] = {
            "label": p["label"],
            "answers": len(recs),
            "own": own or {"name": own_name, "rate": 0, "avg_rank": None, "tier": "未进入"},
            "brands": brands,
            "top_domains": domains.most_common(8),
            "site_types": types.most_common(),
            "own_site_cited": sum(1 for r in recs if any(b["own"] and b["site_cited"] for b in r["analysis"]["brands"])),
            "sentiment": dict(sentiment),
        }
    return out


def summary(records: list[dict], tracked: list[dict]) -> dict:
    """Headline numbers for the client overview; same definitions as the report's metrics()."""
    own_name = next(b["name"] for b in tracked if b.get("own"))
    n = len(records)
    mentioned = own_hits = all_hits = top1 = top3 = 0
    for r in records:
        hits = brand_hits(r, tracked)
        all_hits += len(hits)
        own = next(b for b in r["analysis"]["brands"] if b["own"])
        if not own["mentioned"]:
            continue
        mentioned += 1
        own_hits += 1
        rank = hits.get(own_name) or own["rank"]
        top1 += rank == 1
        top3 += rank <= 3

    def pct(a, b):
        return round(100 * a / b) if b else 0

    return {"rate": pct(mentioned, n), "sov": pct(own_hits, all_hits), "top1": pct(top1, n), "top3": pct(top3, n)}
