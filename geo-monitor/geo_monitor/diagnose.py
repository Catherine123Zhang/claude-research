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
    source_preference: str = Field(description="信源偏好：一句话描述这个平台偏爱引用哪类网站，以及这对品牌意味着什么。")


class Recommendation(BaseModel):
    title: str = Field(description="一句话标题，如“攻坚 Gemini 可见度短板”。")
    basis: str = Field(description="建议依据：引用统计里的具体数字说明为什么要做。")
    action: str = Field(description="建议动作：具体在哪些网站、发什么内容、要达到什么效果。")


class Diagnosis(BaseModel):
    summary: str = Field(description="整体表现：3-4 句总结。")
    platforms: list[PlatformDiagnosis]
    recommendations: list[Recommendation] = Field(description="优化建议：4-6 条，按优先级排序。")


PROMPT = """你是做 GEO（让品牌被 AI 搜索推荐）的分析师。下面是一次监测的统计结果：同一批问题分别问了几个 AI 平台，统计了每个品牌被提到的比例（rate）、在回答里的平均排名（avg_rank）、梯队（tier，T1 最强），以及 AI 引用了哪些网站和哪类网站。

本品牌：{brand}
行业和问题：
{questions}

统计结果（JSON）：
{stats}

请用中文写诊断：
1. summary：整体表现。
2. platforms：每个平台一项，platform_id 用统计里的键。explanation 解释本品牌在该平台的位置和与竞品的差距，结合该平台引用的网站类型推测原因；actions 给出具体动作。
   source_preference 用一句话概括该平台的信源偏好（看 site_types 和 top_domains）。
3. recommendations：整体优化建议，按优先级排序。每条写标题、建议依据（引用具体数字）和建议动作（落到"在哪类网站、发什么内容"，优先利用 AI 已经常引用的网站）。

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
            "source_preference": f"{s['label']} 的引用以{top_type}为主，这类网站上的内容对它的回答影响最大。",
        })
    ranked.sort()
    return {
        "summary": f"{brand} 在 {ranked[-1][1]} 表现最好，在 {ranked[0][1]} 最弱。（示例文字，由模拟数据生成）",
        "platforms": platforms,
        "recommendations": [
            {"title": f"攻坚 {ranked[0][1]} 可见度短板",
             "basis": f"{brand} 在 {ranked[0][1]} 的提及率只有 {round(ranked[0][0] * 100)}%，是所有平台里最低的。",
             "action": f"针对 {ranked[0][1]} 常引用的网站补充产品和资质内容，下次复测时对比提及率。"},
            {"title": "完善 B2B 平台资料",
             "basis": "B2B 平台是各个 AI 引用最多的网站类型之一。",
             "action": "在阿里巴巴国际站、中国制造网完善公司介绍、认证、产品参数和英文 FAQ。"},
            {"title": "补充视频和社区内容",
             "basis": "YouTube、Reddit 出现在多个平台的引用 Top 10 里。",
             "action": "发布工厂实拍、质检流程视频，在相关社区回答采购问题时附上真实案例。"},
        ],
    }
