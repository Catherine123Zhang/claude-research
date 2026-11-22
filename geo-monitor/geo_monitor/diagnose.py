"""Write the per-platform explanation and optimisation advice for a run (爱搜's 诊断报告).

Tiers and numbers come from aggregate.py; Claude only explains them and suggests actions.
"""
from __future__ import annotations

import json

import anthropic
from pydantic import BaseModel, Field


class PlatformDiagnosis(BaseModel):
    platform_id: str
    explanation: str = Field(description="平台差异解释：2-3 句，说明本品牌在这个平台的位置、和竞品的差距、原因。")
    actions: list[str] = Field(description="建议动作：2-3 条，具体到要发什么内容、发在哪类网站。")


class Diagnosis(BaseModel):
    summary: str = Field(description="整体表现：3-4 句总结。")
    platforms: list[PlatformDiagnosis]
    recommendations: list[str] = Field(description="优化建议：4-6 条，按优先级排序。")


PROMPT = """你是做 GEO（让品牌被 AI 搜索推荐）的分析师。下面是一次监测的统计结果：同一批问题分别问了几个 AI 平台，统计了每个品牌被提到的比例（rate）、在回答里的平均排名（avg_rank）、梯队（tier，T1 最强），以及 AI 引用了哪些网站和哪类网站。

本品牌：{brand}
行业和问题：
{questions}

统计结果（JSON）：
{stats}

请用中文写诊断：
1. summary：整体表现。
2. platforms：每个平台一项，platform_id 用统计里的键。explanation 解释本品牌在该平台的位置和与竞品的差距，结合该平台引用的网站类型推测原因；actions 给出具体动作。
3. recommendations：整体优化建议，按优先级排序。要落到"在哪类网站、发什么内容"，优先利用 AI 已经常引用的网站。

只根据给出的数据下结论，数据不足以判断的地方直接说明，不要编造数字。"""


def run_claude(stats: dict, brand: str, questions: list[dict], model: str) -> dict:
    client = anthropic.Anthropic()
    q_text = "\n".join(f"- {q['text']}" for q in questions)
    try:
        response = client.beta.messages.parse(
            model=model,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_format=Diagnosis,
            messages=[{"role": "user", "content": PROMPT.format(
                brand=brand, questions=q_text, stats=json.dumps(stats, ensure_ascii=False, indent=1))}],
        )
    except anthropic.APIStatusError as e:
        raise SystemExit(f"诊断失败：API error {e.status_code}: {e.message}")
    except anthropic.APIConnectionError as e:
        raise SystemExit(f"诊断失败：connection error: {e}")
    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise SystemExit(f"诊断失败：没有得到结果（{response.stop_reason}）")
    return response.parsed_output.model_dump()


def run_mock(stats: dict, brand: str, own_domains: list[str]) -> dict:
    """Fill-in text built from the numbers, for the offline demo."""
    platforms, ranked = [], []
    for pid, s in stats.items():
        own = s["own"]
        leaders = [b["name"] for b in s["brands"] if b["tier"] == "T1" and not b["own"]][:2]
        top_type = s["site_types"][0][0] if s["site_types"] else "其他网站"
        others = [d for d, _ in s["top_domains"] if not any(d == o or d.endswith("." + o) for o in own_domains)]
        top_domain = others[0] if others else "—"
        ranked.append((own["rate"], s["label"]))
        platforms.append({
            "platform_id": pid,
            "explanation": (f"{brand} 在 {s['label']} 的提及率为 {round(own['rate'] * 100)}%，处于{own['tier']}梯队。"
                            f"{'、'.join(leaders) or '没有竞品'}处于第一梯队。该平台最常引用{top_type}，引用最多的第三方网站是 {top_domain}。"),
            "actions": [f"在 {top_domain} 上补充产品页和工厂资质介绍", f"针对{top_type}准备可被引用的对比和选购内容"],
        })
    ranked.sort()
    return {
        "summary": f"{brand} 在 {ranked[-1][1]} 表现最好，在 {ranked[0][1]} 最弱。（示例文字，由模拟数据生成）",
        "platforms": platforms,
        "recommendations": ["在 AI 最常引用的 B2B 平台完善公司和产品资料", "官网补充英文 FAQ 和认证信息，方便被引用",
                            "在 Reddit、YouTube 等社区发布真实的工厂和产品内容", "每周复测，观察提及率变化"],
    }
