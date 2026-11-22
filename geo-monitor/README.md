# GEO 监测（简化版爱搜）

监测你的品牌在 AI 回答里的可见度：把采购商/用户可能问的问题，定期拿去问 ChatGPT、Perplexity、Gemini、Claude（以及豆包、千问、DeepSeek），统计这些指标：

| 指标 | 含义 |
|---|---|
| 提及率 | 回答里提到你品牌的比例 |
| 排名 | 同一条回答里，你排在第几个被提到的品牌 |
| 引用网站 / 站点类型 | AI 列出的参考来源，按视频平台、B2B 平台、问答社区等分类 |
| 官网被引 | 参考来源里有没有你的官网 |
| 搜索关键词 | AI 自己去网上搜了什么（ChatGPT、Gemini、Claude 会返回） |
| 全部品牌、情感倾向 | 由 Claude 读回答后判断（加 `--judge`） |
| 品牌排行 | 所有被提到的品牌（含你没设为竞品的）按提及率、平均排名排序，分平台对比 |
| 被引用的文章 | 每篇被 AI 引用的网页：站点、类型、哪些平台引用、涉及几个问题、引用几次，点开看每条引用记录 |
| 各平台梯队与诊断 | 每个平台里你和竞品分别在 T1/T2/T3 哪一档；加跑 `diagnose` 后由 Claude 写平台差异解释、建议动作和整体优化建议 |

结果生成一个 HTML 看板，可以按平台筛选，点开问题能看到每条回答的原文和引用来源。

## 快速试用（不需要任何 API Key）

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml
python -m geo_monitor run --mock      # 用离线模拟数据
python -m geo_monitor diagnose        # 模拟数据下生成示例诊断文字
python -m geo_monitor report          # 生成 report.html
```

`--mock` 生成的回答全是编造的，只用来看流程和看板，看板顶部会标明"示例数据"。

## 真实运行

1. 在 `config.yaml` 里填品牌名、别名、官网域名、竞品和问题。
2. 设置要用的平台的 API Key（没设 Key 的平台会被记为"请求失败"，不影响其他平台）：

   | 平台 | 环境变量 | 是否联网搜索 |
   |---|---|---|
   | ChatGPT（OpenAI Responses API） | `OPENAI_API_KEY` | 是 |
   | Perplexity（Sonar） | `PERPLEXITY_API_KEY` | 是 |
   | Gemini（Google Search grounding） | `GEMINI_API_KEY` | 是 |
   | Claude（web search 工具） | `ANTHROPIC_API_KEY` | 是 |
   | 豆包（火山方舟应用 + 联网插件） | `ARK_API_KEY` | 是 |
   | 千问（DashScope） | `DASHSCOPE_API_KEY` | 是 |
   | DeepSeek | `DEEPSEEK_API_KEY` | 否，只反映模型记忆 |

3. 运行：

   ```bash
   python -m geo_monitor run --judge     # --judge：用 Claude 识别全部品牌和情感倾向
   python -m geo_monitor diagnose        # 可选：用 Claude 写各平台解释和优化建议
   python -m geo_monitor report
   ```

每次 `run` 的结果追加到 `data/results.jsonl`，`report` 展示最近一次。可以用 cron 每天跑一次。

## 费用估算

调用次数 = 问题数 × 平台数 × 采样次数。示例配置是 5 × 4 × 3 = 60 次，加 `--judge` 再多 60 次 Claude 调用。联网搜索类调用每次一般在几美分以内，具体看各平台价格。

## 和爱搜的区别

- **这里用官方 API，爱搜模拟真人用网页版和 App。** API 的回答和用户在 App 里看到的会有差别（系统提示词、搜索策略不同）。要和 App 完全一致，只能用浏览器自动化或真机去问，这违反多数平台的用户协议，也要维护账号池和代理，这里不做。
- **海外平台 API 都能联网**，做外贸用这个方案基本够用；国内平台里，豆包要在火山方舟建一个开了联网插件的应用，DeepSeek 的 API 不联网。
- 没有"热度值"（关键词搜索量），这需要接百度指数、巨量算数或 Google Keyword Planner 的数据。
- 各平台 HTTP 接口按官方文档编写，但还没用真实 Key 跑过；第一次接入时先用 1 个问题、1 次采样试一下。

## 文件

```
geo_monitor/
  cli.py                 run / report 命令
  analyze.py             品牌提及、排名、引用域名、站点类型
  aggregate.py           各平台统计和梯队
  diagnose.py            Claude 写诊断和优化建议
  llm_judge.py           Claude 识别全部品牌和情感（--judge）
  report_template.html   看板模板
  providers/             各 AI 平台的调用代码；mock.py 是离线模拟
config.example.yaml      配置示例（电动牙刷外贸）
```
