# 🚀 Daily CLI Trending Tools Discovery System

**使用 AI Agent 发现、评估和推荐开放生态中的高质量 CLI 工具**

这是一个完整的系统，用于从 [CLI-Anything](https://github.com/HKUDS/CLI-Anything) 生态发现趋势 CLI 工具，并通过多维度 AI Agent 评估提供高质量推荐。

## 🎯 核心想法

### 问题背景
- 微信/WhatsApp 容易被审查，生态封闭
- 淘宝等消费平台不开放 CLI 接口
- AI Agent 需要标准化、开放的工具生态

### 我们的解决方案
重建一个 **开放、去中心化的 Agent 可用生态**：

```
CLI-Anything 生态（自动将所有软件变成 CLI）
    ↓
每日发现新工具（自动爬取、分类）
    ↓
多维度 AI 评估（Agent 兼容性、质量、趋势）
    ↓
推荐报告（JSON/Markdown/HTML）
    ↓
用户和 Agent 获得高质量工具推荐
```

## 📋 系统组件

### 1. CLI 工具发现 (`cli_trending.py`)
- 从 CLI-Anything 生态爬取工具信息
- 自动分类和标记
- 计算趋势速度 (Trending Velocity)
- 评估 Agent 友好度

**数据结构：**
```python
@dataclass
class CLITool:
    name: str                      # 工具名称
    description: str               # 功能描述
    category: str                  # 分类
    github_url: str                # GitHub 链接
    stars: int                     # GitHub stars
    agent_friendly_score: float    # Agent 友好度评分 (0-100)
    quality_score: float           # 质量评分 (0-100)
    trending_velocity: float       # 趋势速度 (0-100)
```

### 2. Agent 多维度评估 (`agent_evaluator.py`)
使用专门的评估 Agent，从 4 个维度评估每个 CLI：

#### Agent 兼容性维度 (权重: 50%)
- JSON 输出支持
- 命令结构规范性
- 文档质量
- 错误处理机制

#### 质量评估维度 (权重: 35%)
- 代码成熟度
- 测试覆盖率
- 维护活跃度
- 安全风险评估

#### 趋势分析维度 (权重: 15%)
- GitHub 动量（stars/forks 增长率）
- 社区参与度
- 采用轨迹
- 行业采用度

#### 使用场景发现维度
- 实际应用场景
- AI Agent 可用性
- 集成生态

### 3. 报告生成器 (`report_generator.py`)
支持多种输出格式：

- **JSON** - 完整结构化数据，便于集成
- **Markdown** - 易读，便于分享和归档
- **HTML** - 美观的网页报告

### 4. 主系统 (`main.py`)
完整的每日执行管道：
1. 发现新工具
2. AI Agent 多维度评估
3. 生成综合评分
4. 输出报告

## 🔧 使用方式

### 安装依赖
```bash
pip install pyyaml
```

### 运行单次报告
```bash
python main.py
```

输出文件位置：
```
reports/
├── cli_trending_20260708.json       # JSON 格式报告
├── cli_trending_20260708.md         # Markdown 格式报告
├── cli_trending_20260708.html       # HTML 格式报告
└── LATEST.md                         # 最新报告快速访问
```

### 配置

编辑 `config.yaml` 配置：

```yaml
schedule:
  run_time: "09:00"           # 每天运行时间
  timezone: "UTC"

cli_anything:
  poll_interval_hours: 24     # 更新频率

evaluation:
  min_agent_score: 50.0       # 最低 Agent 评分
  min_quality_score: 40.0     # 最低质量评分

notifications:
  email:
    enabled: true
    recipients:
      - your_email@example.com
```

## 📊 报告示例

### JSON 格式
```json
{
  "date": "2026-07-08T09:00:00",
  "total_tools": 50,
  "top_tools": [
    {
      "name": "Ollama CLI",
      "description": "Run large language models locally",
      "category": "AI/ML",
      "agent_friendly_score": 92.5,
      "quality_score": 88.3,
      "trending_velocity": 95.0
    }
  ],
  "trending_score_avg": 82.5
}
```

### Markdown 格式
```markdown
# 🚀 Daily CLI Trending Tools Report

**Date:** 2026-07-08T09:00:00
**Total Tools Analyzed:** 50
**Average Quality Score:** 82.5/100

## 🏆 Top 5 Trending Tools

### 1. Ollama CLI
- **Category:** AI/ML
- **Quality Score:** 88.3/100
- **Agent-Friendly Score:** 92.5/100
...
```

## 🌟 关键特性

### 1. 自动化发现
- 持续监控 CLI-Anything 生态
- 新工具自动入库分类

### 2. AI 驱动评估
- 多个 AI Agent 独立评估
- 多维度综合评分
- 智能聚合结果

### 3. Agent-First 设计
- 所有推荐都考虑 Agent 可用性
- 优先推荐有 JSON 输出的工具
- 帮助 Agent 自动发现新工具

### 4. 开放数据
- 所有报告开放访问
- 结构化 JSON 便于集成
- 支持多种输出格式

## 🔌 与其他系统的集成

### Claude Code 集成
```python
# Agent 可以查询最新的推荐工具
from cli_trending import CLITrendingDiscovery

discovery = CLITrendingDiscovery()
top_tools = await discovery.run_daily_cycle()

# 获取特定分类的工具
ai_tools = top_tools.categories["AI/ML"]
```

### Webhook 通知
配置 webhook URL，系统会在生成报告后自动推送：
```bash
POST {WEBHOOK_URL}
Content-Type: application/json

{
  "event": "daily_report_generated",
  "date": "2026-07-08",
  "total_tools": 50,
  "top_tools": [...]
}
```

### Email 订阅
配置 email 后，每日报告会自动发送到你的邮箱。

## 🎯 使用场景

### 1. **开发者工具发现**
找到最新的、最高质量的 CLI 开发工具

### 2. **AI Agent 工具库构建**
为 Agent 自动发现和推荐可用的 CLI 工具

### 3. **消费场景自动化**
发现新开放 CLI 接口的消费产品（瑞幸、淘宝等）
Agent 可以直接调用完成采购

### 4. **生态监测**
跟踪开放 API/CLI 生态的健康度和趋势

## 🚀 未来扩展

### 短期
- [ ] 从 GitHub 上游自动同步 CLI-Anything 更新
- [ ] 支持社区评价和用户反馈
- [ ] 集成 CI/CD 自动发布

### 中期
- [ ] 支持更多企业服务（Stripe、AWS 等）的 CLI 爬取
- [ ] Agent 自动编写工作流脚本
- [ ] 多语言支持

### 长期
- [ ] 构建完整的开放 Agent 生态平台
- [ ] 去中心化工具注册和发现
- [ ] Agent 市场和工作流交易平台

## 📝 架构设计哲学

这个系统体现的设计理念：

1. **开放而非垄断** - 不是单一公司控制，而是开放标准和生态
2. **自动化驱动** - 最小化人工干预，AI 自动分析和推荐
3. **多维度评估** - 不只看热度，而是综合考虑多个因素
4. **Agent-First** - 所有设计都为 AI 自动化考虑
5. **模块化组件** - 每个模块独立可用，可组合使用

## 📄 许可证

MIT License - 开放和可用于商业用途

## 🤝 贡献

欢迎 Pull Request 和 Issue！

---

**Created:** 2026-07-08  
**Powered by:** Claude Code + CLI-Anything Ecosystem  
**Vision:** Building an Open, Agent-Native Future
