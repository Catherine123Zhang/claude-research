"""Command line for an agency that monitors many clients, each in one or more markets.

    python -m geo_monitor run      [--client ID ...] [--mock] [--judge]
    python -m geo_monitor diagnose [--client ID ...]
    python -m geo_monitor report   [--client ID ...]
    python -m geo_monitor pdf      [--client ID ...]

Without --client every file in clients/ is processed. A client is clients/<id>.yaml;
its results live in data/<id>/ and its report in reports/<id>.html.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import yaml

from .aggregate import brand_hits, platform_stats, summary
from .analyze import analyze, site_name
from .diagnose import run_mock
from .providers import Answer, build_provider
from .providers.mock import MockProvider

TEMPLATE = Path(__file__).with_name("report_template.html")
CLIENTS_DIR = Path("clients")
REPORTS_DIR = Path("reports")
AGENCY_FILE = Path("agency.yaml")
DOMESTIC_IDS = {"domestic", "cn", "china", "国内"}


# ---------- config ----------

def load_client(path: Path) -> dict:
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    cfg["id"] = str(cfg.get("id") or path.stem)
    brand = cfg["brand"]
    brand.setdefault("aliases", [brand["name"]])
    brand.setdefault("domains", [])
    cfg.setdefault("name", brand["name"])
    cfg.setdefault("competitors", [])
    cfg.setdefault("samples", 1)
    if "markets" not in cfg:  # single-market config from earlier versions
        cfg["markets"] = [{"id": "default", "label": "默认", "region": cfg.get("region"),
                           "questions": cfg.pop("questions"), "platforms": cfg.pop("platforms")}]
    for m in cfg["markets"]:
        m.setdefault("label", m["id"])
        m.setdefault("kind", "domestic" if m["id"] in DOMESTIC_IDS else "overseas")
        m.setdefault("samples", cfg["samples"])
        for p in m["platforms"]:
            p.setdefault("label", p["id"])
    cfg["data_dir"] = Path(cfg.get("data_dir") or f"data/{cfg['id']}")
    return cfg


def resolve_clients(ids: list[str] | None, legacy_config: str | None) -> list[dict]:
    if legacy_config:
        return [load_client(Path(legacy_config))]
    if ids:
        paths = [Path(i) if i.endswith((".yaml", ".yml")) else CLIENTS_DIR / f"{i}.yaml" for i in ids]
    else:
        paths = sorted(CLIENTS_DIR.glob("*.yaml"))
    if not paths:
        sys.exit("没有找到客户配置。把 clients/example.yaml 复制一份改成你的客户，或用 --client 指定文件。")
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        sys.exit(f"找不到客户配置：{', '.join(missing)}")
    return [load_client(p) for p in paths]


def tracked_brands(cfg: dict, market: dict) -> list[dict]:
    own = {**cfg["brand"], "own": True}
    comps = market.get("competitors", cfg["competitors"])
    others = [{**c, "aliases": c.get("aliases") or [c["name"]], "domains": c.get("domains", []), "own": False}
              for c in comps]
    return [own, *others]


def load_agency() -> dict:
    if not AGENCY_FILE.exists():
        return {}
    agency = yaml.safe_load(AGENCY_FILE.read_text(encoding="utf-8")) or {}
    logo = agency.get("logo")
    if logo and Path(logo).exists():
        mime = {"svg": "image/svg+xml", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(
            Path(logo).suffix.lower().lstrip("."), "image/png")
        agency["logo_data"] = f"data:{mime};base64,{base64.b64encode(Path(logo).read_bytes()).decode()}"
    return agency


# ---------- run ----------

def run_client(cfg: dict, mock: bool, use_judge: bool, workers: int) -> None:
    run_id = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    judge = None
    if use_judge and not mock:
        from .llm_judge import LLMJudge

        judge = LLMJudge(model=cfg.get("judge_model", "claude-opus-5-5"))

    jobs = []
    for m in cfg["markets"]:
        brands = tracked_brands(cfg, m)
        for p in m["platforms"]:
            for qi, q in enumerate(m["questions"]):
                for s in range(m["samples"]):
                    jobs.append((m, brands, p, qi, q, s))

    def one(job):
        m, brands, p, qi, q, s = job
        provider = None
        try:
            if mock:
                provider = MockProvider(p["id"], [b["name"] for b in brands], sample=s, run_id=run_id,
                                        kind=m["kind"], own_domain=(cfg["brand"]["domains"] or ["example.com"])[0])
            else:
                provider = build_provider(p, region=m.get("region"))
            ans = provider.ask(q["text"])
        except Exception as e:  # noqa: BLE001 - missing key, bad config: record it and keep going
            ans = Answer(error=f"{type(e).__name__}: {e}")
        rec = {
            "run_id": run_id, "market": m["id"], "platform": p["id"], "q": qi, "question": q["text"],
            "category": q.get("category", ""), "sample": s, "model": ans.model, "text": ans.text,
            "citations": ans.citations, "queries": ans.queries, "error": ans.error, "mock": mock,
        }
        if not ans.error:
            rec["analysis"] = analyze(ans.text, ans.citations, brands)
            if mock:
                rec["judge"] = provider.judge(ans.text)
            elif judge:
                rec["judge"] = judge.judge(q["text"], ans.text, cfg["brand"]["name"], cfg["brand"]["aliases"])
        status = "失败: " + ans.error if ans.error else "完成"
        print(f"[{cfg['id']}/{m['id']}/{p['id']}] Q{qi + 1} #{s + 1} {status}", file=sys.stderr)
        return rec

    with ThreadPoolExecutor(max_workers=workers) as pool:
        records = list(pool.map(one, jobs))

    cfg["data_dir"].mkdir(parents=True, exist_ok=True)
    out = cfg["data_dir"] / "results.jsonl"
    with out.open("a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    failed = sum(1 for r in records if r["error"])
    print(f"{cfg['name']} 本次运行 {run_id}: {len(records)} 条回答，失败 {failed} 条，已写入 {out}", file=sys.stderr)


# ---------- reading results ----------

def all_rows(cfg: dict) -> list[dict]:
    path = cfg["data_dir"] / "results.jsonl"
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for r in rows:
        r.setdefault("market", "default")
    return rows


def market_runs(rows: list[dict], market_id: str) -> list[str]:
    return sorted({r["run_id"] for r in rows if r["market"] == market_id})


def records_of(rows: list[dict], market_id: str, run_id: str) -> list[dict]:
    return [r for r in rows if r["market"] == market_id and r["run_id"] == run_id]


def trend(rows: list[dict], market_id: str, tracked: list[dict], last: int = 12) -> dict:
    """Mention rate of every brand in each of the market's last `last` runs."""
    runs = market_runs(rows, market_id)[-last:]
    rates: dict[str, list[float]] = {}
    for i, run in enumerate(runs):
        recs = [r for r in records_of(rows, market_id, run) if not r.get("error")]
        for r in recs:
            for name in brand_hits(r, tracked):
                rates.setdefault(name, [0.0] * len(runs))[i] += 1 / len(recs)
    return {"runs": runs, "rates": {k: [round(v, 3) for v in vs] for k, vs in rates.items()}}


def question_gaps(records: list[dict], market: dict, tracked: list[dict], own_domains: list[str]) -> list[dict]:
    """Per question: how often the brand is mentioned and which third-party sites the answers cite most."""
    out = []
    for qi, q in enumerate(market["questions"]):
        rs = [r for r in records if r["q"] == qi and not r.get("error")]
        if not rs:
            continue
        rate = summary(rs, tracked)["rate"]
        cited: dict[str, int] = {}
        for r in rs:
            for d in set(r["analysis"]["domains"]):
                if d and not any(d == o or d.endswith("." + o) for o in own_domains):
                    cited[d] = cited.get(d, 0) + 1
        out.append({"question": q["text"], "mention_rate": rate,
                    "cited_sites": [site_name(d) for d, _ in sorted(cited.items(), key=lambda x: -x[1])[:5]]})
    return sorted(out, key=lambda g: g["mention_rate"])


def diagnosis_path(cfg: dict, market_id: str, run_id: str) -> Path:
    return cfg["data_dir"] / f"diagnosis-{market_id}-{run_id.replace(':', '')}.json"


# ---------- diagnose ----------

def diagnose_client(cfg: dict) -> None:
    rows = all_rows(cfg)
    if not rows:
        print(f"{cfg['name']}：还没有运行结果，跳过。", file=sys.stderr)
        return
    for m in cfg["markets"]:
        runs = market_runs(rows, m["id"])
        if not runs:
            continue
        latest = records_of(rows, m["id"], runs[-1])
        tracked = tracked_brands(cfg, m)
        ran = {r["platform"] for r in latest}
        stats = platform_stats(latest, tracked, [p for p in m["platforms"] if p["id"] in ran])
        gaps = question_gaps(latest, m, tracked, cfg["brand"]["domains"])
        if any(r.get("mock") for r in latest):
            result = run_mock(stats, cfg["brand"]["name"], cfg["brand"]["domains"], gaps)
        else:
            from .diagnose import run_claude

            where = m["label"] + (f"（地区 {m['region']}）" if m.get("region") else "")
            result = run_claude(stats, cfg["brand"]["name"], m["questions"], cfg.get("judge_model", "claude-opus-5-5"),
                                market=where, gaps=gaps)
        out = diagnosis_path(cfg, m["id"], runs[-1])
        out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{cfg['name']} · {m['label']} 诊断已生成: {out}", file=sys.stderr)


# ---------- report ----------

SLIM_KEYS = ("platform", "q", "error", "judge")


def slim(records: list[dict]) -> list[dict]:
    """Just enough of each answer to recompute the headline numbers of an earlier run."""
    return [{**{k: r.get(k) for k in SLIM_KEYS}, "analysis": {"brands": (r.get("analysis") or {}).get("brands", [])}}
            for r in records]


def market_data(cfg: dict, m: dict, rows: list[dict]) -> dict | None:
    runs = market_runs(rows, m["id"])
    if not runs:
        return None
    run_id = runs[-1]
    latest = records_of(rows, m["id"], run_id)
    tracked = tracked_brands(cfg, m)
    ran = {r["platform"] for r in latest}
    diag = diagnosis_path(cfg, m["id"], run_id)
    baseline_id = m.get("baseline_run") or cfg.get("baseline_run") or runs[0]
    # "上次" is the run before this one; "基线" is the run before optimisation started (first run unless set).
    compare = {}
    if len(runs) >= 2:
        compare["previous"] = {"run_id": runs[-2], "records": slim(records_of(rows, m["id"], runs[-2]))}
    if baseline_id in runs and baseline_id != run_id:
        compare["baseline"] = {"run_id": baseline_id, "records": slim(records_of(rows, m["id"], baseline_id))}
    return {
        "id": m["id"], "label": m["label"], "kind": m["kind"], "region": m.get("region"),
        "run_id": run_id, "runs": len(runs), "samples": m["samples"],
        "mock": any(r.get("mock") for r in latest),
        "brands": [{"name": b["name"], "own": b["own"], "aliases": b["aliases"]} for b in tracked],
        "platforms": [{"id": p["id"], "label": p["label"]} for p in m["platforms"] if p["id"] in ran],
        "questions": [{"text": q["text"], "category": q.get("category", "")} for q in m["questions"]],
        "records": [{k: r.get(k) for k in ("platform", "q", "sample", "text", "citations", "queries",
                                              "error", "analysis", "judge")} for r in latest],
        "stats": platform_stats(latest, tracked, [p for p in m["platforms"] if p["id"] in ran]),
        "trend": trend(rows, m["id"], tracked),
        "site_names": {d: site_name(d) for r in latest if not r.get("error") for d in r["analysis"]["domains"] if d},
        "diagnosis": json.loads(diag.read_text(encoding="utf-8")) if diag.exists() else None,
        "compare": compare,
    }


def wrap_html(body: str) -> str:
    return ('<!doctype html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '<style>body{margin:0}[hidden]{display:none!important}</style>\n</head>\n<body>\n'
            + body + "\n</body>\n</html>\n")


def report_client(cfg: dict, agency: dict, out_path: Path, fragment: bool = False) -> dict | None:
    rows = all_rows(cfg)
    markets = [d for m in cfg["markets"] if (d := market_data(cfg, m, rows))]
    if not markets:
        print(f"{cfg['name']}：还没有运行结果，跳过报告。", file=sys.stderr)
        return None
    data = {
        "client": cfg["name"], "brand": cfg["brand"], "agency": {k: v for k, v in agency.items() if k != "logo"},
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "markets": markets,
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    body = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", payload)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(body if fragment else wrap_html(body), encoding="utf-8")
    print(f"{cfg['name']} 报告已生成: {out_path}", file=sys.stderr)
    tracked = {m["id"]: tracked_brands(cfg, m) for m in cfg["markets"]}
    return {
        "id": cfg["id"], "name": cfg["name"], "file": out_path.name,
        "markets": [{"label": d["label"], "region": d["region"], "run_id": d["run_id"], "mock": d["mock"],
                     **summary([r for r in d["records"] if not r.get("error")], tracked[d["id"]]),
                     "prev": summary([r for r in d["compare"].get("previous", {}).get("records", []) if not r.get("error")],
                                     tracked[d["id"]]) if "previous" in d["compare"] else None}
                    for d in markets],
    }


INDEX_STYLE = """
:root { --bg: #f3f5f4; --surface: #fff; --ink: #14211f; --muted: #5d6b68; --line: #dbe2e0; --accent: #0e7c6b; --warn: #b45309; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg: #0f1615; --surface: #172120; --ink: #e5eeec; --muted: #93a5a1; --line: #2a3735; --accent: #3cc3a9; --warn: #f0a44b; color-scheme: dark } }
:root[data-theme="dark"] { --bg: #0f1615; --surface: #172120; --ink: #e5eeec; --muted: #93a5a1; --line: #2a3735; --accent: #3cc3a9; --warn: #f0a44b; color-scheme: dark }
body { background: var(--bg); color: var(--ink); font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif; font-size: 15px; }
.wrap { max-width: 1000px; margin: 0 auto; padding-block: 28px 48px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
h1 { font-size: 26px; margin: 0 0 4px; } .sub { color: var(--muted); margin: 0 0 20px; }
.scroll { overflow-x: auto; } table { border-collapse: collapse; width: 100%; background: var(--surface); border-radius: 10px; }
th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { color: var(--muted); font-weight: 500; font-size: 13px; } td.num { font-variant-numeric: tabular-nums; white-space: nowrap; }
a { color: var(--accent); } .up { color: var(--accent); } .down { color: var(--warn); } .tag { font-size: 12px; color: var(--muted); }
"""


def write_index(entries: list[dict], agency: dict) -> Path:
    def delta(cur, prev, key):
        if not prev or prev.get(key) is None or cur.get(key) is None:
            return ""
        d = cur[key] - prev[key]
        if d == 0:
            return ' <span class="tag">持平</span>'
        return f' <span class="{"up" if d > 0 else "down"}">{"▲" if d > 0 else "▼"}{abs(d)}</span>'

    rows = []
    for e in entries:
        for i, m in enumerate(e["markets"]):
            name = f'<a href="{e["file"]}">{e["name"]}</a>' if i == 0 else ""
            region = f'（{m["region"]}）' if m["region"] else ""
            sample = ' <span class="tag">示例数据</span>' if m["mock"] else ""
            rows.append(f"<tr><td>{name}</td><td>{m['label']}{region}{sample}</td>"
                        f"<td class='num'>{m['rate']}%{delta(m, m['prev'], 'rate')}</td>"
                        f"<td class='num'>{m['sov']}%{delta(m, m['prev'], 'sov')}</td>"
                        f"<td class='num'>{m['top3']}%{delta(m, m['prev'], 'top3')}</td>"
                        f"<td class='num'>{m['run_id'].replace('T', ' ')[:16]}</td></tr>")
    title = f"{agency.get('name', '')} 客户 GEO 总览".strip()
    body = (f"<title>客户 GEO 总览</title><style>{INDEX_STYLE}</style><div class='wrap'><h1>{title}</h1>"
            f"<p class='sub'>每个客户各市场最近一次监测的品牌提及率、SOV 和 Top3 提及率；箭头是和上一次相比的变化（百分点）。点客户名打开完整报告。</p>"
            "<div class='scroll'><table><thead><tr><th>客户</th><th>市场</th><th>提及率</th><th>SOV</th><th>Top3 提及率</th><th>最近监测</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div></div>")
    out = REPORTS_DIR / "index.html"
    out.write_text(wrap_html(body), encoding="utf-8")
    print(f"客户总览已生成: {out}", file=sys.stderr)
    return out


# ---------- pdf ----------

def pdf_client(cfg: dict) -> None:
    html = REPORTS_DIR / f"{cfg['id']}.html"
    if not html.exists():
        sys.exit(f"先运行 report 生成 {html}")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("导出 PDF 需要 Playwright：pip install playwright && playwright install chromium")
    import os

    markets = [m["id"] for m in cfg["markets"]]
    with sync_playwright() as p:
        exe = os.environ.get("GEO_CHROMIUM")  # optional: use an already-installed Chromium
        browser = p.chromium.launch(**({"executable_path": exe} if exe else {}))
        page = browser.new_page(viewport={"width": 1200, "height": 900})
        for mid in markets:  # one PDF per market; the report opens the market named in the URL hash
            out = html.with_name(f"{cfg['id']}-{mid}.pdf" if len(markets) > 1 else f"{cfg['id']}.pdf")
            page.goto(html.resolve().as_uri() + f"#{mid}")
            page.reload()
            page.emulate_media(media="print")
            page.pdf(path=str(out), format="A4", print_background=True,
                     margin={"top": "14mm", "bottom": "14mm", "left": "10mm", "right": "10mm"})
            print(f"{cfg['name']} PDF 已生成: {out}", file=sys.stderr)
        browser.close()


# ---------- entry ----------

def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="geo_monitor", description="AI 搜索可见度监测（多客户、多市场）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--client", action="append", help="客户 ID（clients/<ID>.yaml）或配置文件路径；可写多次。不写则处理全部客户")
        sp.add_argument("--config", help=argparse.SUPPRESS)  # earlier single-config usage

    r = sub.add_parser("run", help="向各个 AI 平台提问并保存结果")
    common(r)
    r.add_argument("--mock", action="store_true", help="用离线模拟数据，不调用任何 API")
    r.add_argument("--judge", action="store_true", help="用 Claude 识别回答里的全部品牌和情感倾向")
    r.add_argument("--workers", type=int, default=4)
    common(sub.add_parser("diagnose", help="用 Claude 给每个市场最近一次运行写解释和优化建议"))
    g = sub.add_parser("report", help="生成每个客户的 HTML 报告和客户总览")
    common(g)
    g.add_argument("--fragment", action="store_true", help=argparse.SUPPRESS)
    g.add_argument("--out", help=argparse.SUPPRESS)
    common(sub.add_parser("pdf", help="把客户报告导出成 PDF（需要 Playwright）"))
    dl = sub.add_parser("daily", help="一次跑完 run → diagnose → report（→ pdf），适合设成每天定时运行")
    common(dl)
    dl.add_argument("--judge", action="store_true")
    dl.add_argument("--pdf", action="store_true", help="同时导出 PDF")
    dl.add_argument("--mock", action="store_true", help=argparse.SUPPRESS)
    dl.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)

    clients = resolve_clients(args.client, args.config)
    if args.cmd == "run":
        for cfg in clients:
            run_client(cfg, args.mock, args.judge, args.workers)
    elif args.cmd == "diagnose":
        for cfg in clients:
            diagnose_client(cfg)
    elif args.cmd == "report":
        agency = load_agency()
        entries = []
        for cfg in clients:
            out = Path(args.out) if args.out and len(clients) == 1 else REPORTS_DIR / f"{cfg['id']}.html"
            if e := report_client(cfg, agency, out, args.fragment):
                entries.append(e)
        if entries and not args.fragment:
            write_index(entries, agency)
    elif args.cmd == "pdf":
        for cfg in clients:
            pdf_client(cfg)
    else:  # daily
        agency = load_agency()
        entries = []
        for cfg in clients:
            run_client(cfg, args.mock, args.judge, args.workers)
            diagnose_client(cfg)
            if e := report_client(cfg, agency, REPORTS_DIR / f"{cfg['id']}.html"):
                entries.append(e)
            if args.pdf:
                pdf_client(cfg)
        if entries:
            write_index(entries, agency)
