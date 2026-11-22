"""Command line: ask the AI platforms, then build the dashboard.

    python -m geo_monitor run    --config config.yaml [--mock] [--judge]
    python -m geo_monitor report --config config.yaml [--out report.html]
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import yaml

from .analyze import analyze
from .providers import build_provider
from .providers.mock import MockProvider

TEMPLATE = Path(__file__).with_name("report_template.html")


def load_config(path: str) -> dict:
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    brand = cfg["brand"]
    brand.setdefault("aliases", [brand["name"]])
    brand.setdefault("domains", [])
    cfg.setdefault("competitors", [])
    cfg.setdefault("samples", 1)
    cfg.setdefault("results_file", "data/results.jsonl")
    for p in cfg["platforms"]:
        p.setdefault("label", p["id"])
    return cfg


def tracked_brands(cfg: dict) -> list[dict]:
    own = {**cfg["brand"], "own": True}
    others = [{**c, "aliases": c.get("aliases") or [c["name"]], "domains": c.get("domains", []), "own": False}
              for c in cfg["competitors"]]
    return [own, *others]


def cmd_run(cfg: dict, mock: bool, use_judge: bool, workers: int) -> None:
    brands = tracked_brands(cfg)
    brand_names = [b["name"] for b in brands]
    run_id = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    judge = None
    if use_judge and not mock:
        from .llm_judge import LLMJudge

        judge = LLMJudge(model=cfg.get("judge_model", "claude-opus-5-5"))

    jobs = []
    for p in cfg["platforms"]:
        for qi, q in enumerate(cfg["questions"]):
            for s in range(cfg["samples"]):
                jobs.append((p, qi, q, s))

    def one(job):
        p, qi, q, s = job
        try:
            provider = MockProvider(p["id"], brand_names, sample=s) if mock else build_provider(p)
            ans = provider.ask(q["text"])
        except Exception as e:  # noqa: BLE001 - missing key, bad config: record it and keep going
            from .providers import Answer

            provider, ans = None, Answer(error=f"{type(e).__name__}: {e}")
        rec = {
            "run_id": run_id, "platform": p["id"], "q": qi, "question": q["text"], "category": q.get("category", ""),
            "sample": s, "model": ans.model, "text": ans.text, "citations": ans.citations,
            "queries": ans.queries, "error": ans.error, "mock": mock,
        }
        if not ans.error:
            rec["analysis"] = analyze(ans.text, ans.citations, brands)
            if mock:
                rec["judge"] = provider.judge(ans.text)
            elif judge:
                rec["judge"] = judge.judge(q["text"], ans.text, cfg["brand"]["name"], cfg["brand"]["aliases"])
        status = "失败: " + ans.error if ans.error else "完成"
        print(f"[{p['id']}] Q{qi + 1} #{s + 1} {status}", file=sys.stderr)
        return rec

    with ThreadPoolExecutor(max_workers=workers) as pool:
        records = list(pool.map(one, jobs))

    out = Path(cfg["results_file"])
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    failed = sum(1 for r in records if r["error"])
    print(f"本次运行 {run_id}: {len(records)} 条回答，失败 {failed} 条，已写入 {out}", file=sys.stderr)


def cmd_report(cfg: dict, out_path: str, fragment: bool) -> None:
    path = Path(cfg["results_file"])
    if not path.exists():
        sys.exit(f"没有找到结果文件 {path}，请先运行 run。")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    run_id = max(r["run_id"] for r in rows)
    latest = [r for r in rows if r["run_id"] == run_id]
    ran = {r["platform"] for r in latest}
    data = {
        "run_id": run_id,
        "mock": any(r.get("mock") for r in latest),
        "samples": cfg["samples"],
        "brand": cfg["brand"],
        "brands": [{"name": b["name"], "own": b["own"], "aliases": b["aliases"]} for b in tracked_brands(cfg)],
        "platforms": [{"id": p["id"], "label": p["label"]} for p in cfg["platforms"] if p["id"] in ran],
        "questions": [{"text": q["text"], "category": q.get("category", "")} for q in cfg["questions"]],
        "records": [{k: r.get(k) for k in ("platform", "q", "sample", "text", "citations", "queries",
                                              "error", "analysis", "judge")} for r in latest],
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    body = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", payload)
    if not fragment:
        body = ('<!doctype html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                '<style>body{margin:0}[hidden]{display:none!important}</style>\n</head>\n<body>\n'
                + body + "\n</body>\n</html>\n")
    Path(out_path).write_text(body, encoding="utf-8")
    print(f"看板已生成: {out_path}", file=sys.stderr)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="geo_monitor", description="AI 搜索可见度监测")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="向各个 AI 平台提问并保存结果")
    r.add_argument("--config", default="config.yaml")
    r.add_argument("--mock", action="store_true", help="用离线模拟数据，不调用任何 API")
    r.add_argument("--judge", action="store_true", help="用 Claude 识别回答里的全部品牌和情感倾向")
    r.add_argument("--workers", type=int, default=4)
    g = sub.add_parser("report", help="把最近一次运行生成 HTML 看板")
    g.add_argument("--config", default="config.yaml")
    g.add_argument("--out", default="report.html")
    g.add_argument("--fragment", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    if args.cmd == "run":
        cmd_run(cfg, args.mock, args.judge, args.workers)
    else:
        cmd_report(cfg, args.out, args.fragment)
