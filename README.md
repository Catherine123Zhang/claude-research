# Claude Research & Experiments

Repository for Claude-related research and experimental projects.

## 🚀 Projects

### 1. Daily CLI Trending Tools Discovery System
**Discovery, evaluation, and recommendation of AI-friendly CLI tools**

From the vision: *"Rebuild an open, decentralized ecosystem where AI agents can interact with real software"*

This system transforms the [CLI-Anything](https://github.com/HKUDS/CLI-Anything) ecosystem into a daily discovery and recommendation platform.

**Key Features:**
- 🤖 Automatic CLI tool discovery from CLI-Anything
- 📊 Multi-dimensional AI agent evaluation
- 🎯 Agent compatibility scoring (JSON support, command structure, documentation)
- 📈 Trending analysis and adoption tracking
- 📄 Multi-format reporting (JSON, Markdown, HTML)

**Getting Started:**
```bash
python main.py              # Generate daily report
```

**Documentation:** [DAILY_CLI_TOOLS.md](DAILY_CLI_TOOLS.md)

**Output Examples:**
- `reports/cli_trending_YYYYMMDD.json` — Structured data for integration
- `reports/cli_trending_YYYYMMDD.md` — Readable daily report
- `reports/cli_trending_YYYYMMDD.html` — Beautiful web report

### 2. Claude System Prompts Research
Reverse-engineered system prompts from Anthropic's Claude models.

- `CLAUDE-FABLE-5.md` — Claude Fable 5 (Mythos-class, 2026) full system prompt from [CL4R1T4S](https://github.com/elder-plinius/CL4R1T4S)

## Architecture

This repository demonstrates:
1. **AI-Driven Discovery** - Using AI agents to discover and evaluate tools
2. **Open Ecosystem Design** - Moving away from proprietary platforms
3. **Agent-Native Systems** - Building for AI automation from the start
4. **Multi-Format Delivery** - Adapting output for different consumption patterns

## Vision

Building the infrastructure for an **agent-native, open-source future** where:
- AI agents can interact with real professional software
- Tools are evaluated for both human and machine consumption
- Ecosystems are open and not controlled by single companies
- Discovery and integration happen automatically

This contrasts with closed platforms like WeChat or Taobao, which require manual integration and limit AI automation possibilities.

## Files

```
.
├── README.md                      # This file
├── DAILY_CLI_TOOLS.md             # System documentation
├── config.yaml                    # Configuration
│
├── cli_trending.py                # Core discovery system
├── report_generator.py            # Multi-format report generation
├── agent_evaluator.py             # AI agent evaluation framework
├── main.py                        # Main entry point
│
├── reports/                       # Generated daily reports
│   ├── cli_trending_YYYYMMDD.json
│   ├── cli_trending_YYYYMMDD.md
│   ├── cli_trending_YYYYMMDD.html
│   └── LATEST.md
│
└── CLAUDE-FABLE-5.md             # Claude system prompt research
```

## Quick Start

1. **Install dependencies**
   ```bash
   pip install pyyaml
   ```

2. **Run daily discovery**
   ```bash
   python main.py
   ```

3. **View reports**
   ```bash
   open reports/LATEST.md
   ```

4. **Configure** (optional)
   ```bash
   # Edit config.yaml for custom settings
   ```

## Contributing

This is an experimental research project. Contributions welcome for:
- Additional CLI tool sources
- Improved evaluation dimensions
- New report formats
- Integration examples

## License

MIT - Open for research and commercial use
