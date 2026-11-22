# GEO 监测（多客户、多市场）

给 SEO / GEO 服务商用的 AI 搜索可见度监测工具：为每个客户定期向海外和国内的 AI 平台提问，统计客户品牌有没有被提到、排第几、AI 引用了哪些网站，生成可以直接交给客户的报告。

## 报告里有什么

| 模块 | 内容 |
|---|---|
| 市场对比 | 一个客户同时做海外和国内时，各市场核心指标并排对比；点市场按钮切换完整数据 |
| 数据概览 | 对话次数、提及率、提及次数、SOV、Top1 / Top3 提及率、平均排名、好感度、官网被引；每项带**较上次**和**较基线**（优化前）的变化 |
| 平台表现 | 以上指标按 AI 平台分列 |
| 提及率热力图 | 问题 × 平台，可切换整体 / Top1 / Top3 |
| 提及率趋势 | 最近 12 次监测里你和主要竞品的变化 |
| 品牌排行 | 所有被提到的品牌（含没设为竞品、由 `--judge` 发现的）按提及率和平均排名排序 |
| 品牌竞争位置 | 散点图：横轴提及率、纵轴平均排名、圆大小为被提到次数 |
| 梯队与诊断 | 每个平台里你和竞品在 T1 / T2 / T3 哪一档、平台偏好哪类信源；`diagnose` 后有 Claude 写的解释和建议动作 |
| 优化建议 | 标题 + 建议依据 + 建议动作 |
| 内容缺口与选题 | 提及率低的问题、哪些平台没提到你、AI 回答时引用最多的网站（去哪里发），以及 Claude 给的选题 |
| 引用来源 | 各平台引用 Top 10、被引用的文章（点开看每条引用记录） |
| 问题明细 | 每条回答原文、AI 的搜索关键词、提及的全部品牌、情感、引用来源 |

另外生成 `reports/index.html`：所有客户、所有市场的提及率 / SOV / Top3 一览，带和上次相比的涨跌。

## 快速试用（不需要任何 API Key）

```bash
pip install -r requirements.txt
python -m geo_monitor run --mock          # 用离线模拟数据跑 clients/ 里的所有示例客户
python -m geo_monitor diagnose            # 模拟数据下生成示例诊断
python -m geo_monitor report              # 生成 reports/<客户>.html 和 reports/index.html
```

`--mock` 生成的回答全是编造的，报告顶部会标明"示例数据"。

## 加客户

每个客户一个文件 `clients/<客户ID>.yaml`，参考 `clients/example-jideng.yaml`（海外 + 国内）和 `clients/example-novacos.yaml`（只做东南亚）。要点：

- `brand.aliases` 写全中英文写法，`brand.domains` 写官网域名。
- `markets` 下每个市场有自己的 `questions`、`platforms`、`competitors`；市场 `id` 只用英文字母、数字和连字符（报告网址里会用到）。
- 海外市场写 `region`（如 `US`、`VN`），ChatGPT、Claude、Perplexity、Grok 会按这个国家的用户来回答。
- `baseline_run` 填开始优化前那次运行的时间，报告里的"较基线"就和它比；不填用第一次运行。

命令都支持 `--client <ID>` 只处理某个客户（可写多次），不写则处理全部。

## 服务商品牌

复制 `agency.example.yaml` 为 `agency.yaml`，填公司名、Logo（PNG/JPG/SVG）、网址、联系方式。报告页眉、页脚和客户总览会显示这些信息。

## 真实运行

设置要用的平台的 API Key（没设 Key 的平台记为"请求失败"，不影响其他平台）：

| 市场 | 平台 | `type` | 环境变量 | 联网搜索 |
|---|---|---|---|---|
| 海外 | ChatGPT | `openai` | `OPENAI_API_KEY` | 是 |
| 海外 | Perplexity | `perplexity` | `PERPLEXITY_API_KEY` | 是 |
| 海外 | Gemini | `gemini` | `GEMINI_API_KEY` | 是（不支持按地区） |
| 海外 | Claude | `claude` | `ANTHROPIC_API_KEY` | 是 |
| 海外 | Grok | `grok` | `XAI_API_KEY` | 是 |
| 国内 | 豆包 | `doubao_bot` | `ARK_API_KEY`（`model` 填开了联网插件的火山方舟应用 ID） | 是 |
| 国内 | 千问 | `qwen` | `DASHSCOPE_API_KEY` | 是 |
| 国内 | Kimi | `kimi` | `MOONSHOT_API_KEY` | 是 |
| 国内 | DeepSeek | `deepseek` | `DEEPSEEK_API_KEY` | 否，只反映模型记忆 |

```bash
python -m geo_monitor run --judge     # --judge：用 Claude 识别全部品牌和情感倾向
python -m geo_monitor diagnose        # 用 Claude 写各市场的诊断、建议和选题
python -m geo_monitor report
python -m geo_monitor pdf             # 每个客户每个市场导出一份 PDF（需要 pip install playwright && playwright install chromium）
```

## 每天自动运行

`daily` 一次跑完 run → diagnose → report（加 `--pdf` 再导出 PDF）：

```bash
python -m geo_monitor daily --judge --pdf
```

- **Mac / Linux**：`crontab -e` 加一行，每天早上 8:30 跑：
  `30 8 * * * cd /path/to/geo-monitor && python3 -m geo_monitor daily --judge --pdf >> daily.log 2>&1`
- **Windows**：任务计划程序 → 创建基本任务 → 每天 → 程序填 `python`，参数填 `-m geo_monitor daily --judge --pdf`，起始于填项目目录。

## 费用

调用次数 ≈ 问题数 × 平台数 × 采样次数，每个市场分别算；加 `--judge` 每条回答再多一次 Claude 调用，`diagnose` 每个市场一次。示例客户吉登：海外 4×5×3 + 国内 4×4×3 = 108 次。

## 和爱搜等工具的区别

- 这里用**官方 API**，爱搜模拟真人用网页版和 App。API 的回答和 App 里看到的会有差别；App 端（豆包手机版、AI 抖音、商品卡等）拿不到。
- Google AI Overview / AI Mode 和 Microsoft Copilot 没有官方 API，未接入。
- 没有"热度值"（关键词搜索量）。
- Grok、Kimi、豆包应用、千问联网的接口按官方文档编写，还没用真实 Key 跑过；第一次接入时先用一个客户、1 次采样试一下。

## 文件

```
clients/                 客户配置，一个客户一个 yaml（示例：example-*.yaml）
agency.example.yaml      服务商品牌信息模板
geo_monitor/
  cli.py                 run / diagnose / report / pdf / daily 命令
  analyze.py             品牌提及、排名、引用域名、站点名称和类型
  aggregate.py           各平台统计、梯队、汇总指标
  llm_judge.py           Claude 识别全部品牌和情感（--judge）
  diagnose.py            Claude 写诊断、建议和选题
  report_template.html   报告模板
  providers/             各 AI 平台的调用代码；mock.py 是离线模拟
data/<客户>/             每次运行的原始结果和诊断（不提交到仓库）
reports/                 生成的报告和 PDF（不提交到仓库）
```
