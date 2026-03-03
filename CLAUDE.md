# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目开发规范与文档标准
在本次会话及所有代码生成任务中，必须严格遵守以下开发规范。

1. 文档注释规范
1.1 文件头注释标准
所有代码文件（如 .py, .js, .ts 等）必须在文件开头包含清晰的注释块。注释块需包含以下关键信息：

Contains (包含内容): 列出文件中定义的主要函数、类或组件名称。
Responsibilities (负责功能): 明确该文件的核心职责和功能点。
Non-Responsibilities (不负责功能): 明确界定该文件不处理的内容，防止职责扩散。
Input (输入): 描述该文件接收的输入数据来源、格式或类型。
Output (输出): 描述该文件产出的结果、副作用或返回值。
示例模板：

"""@File: example_module.py@Contains: [function_a, ClassB]@Responsibilities:    - 负责处理用户数据的清洗与格式化    - 负责生成数据报表@Non-Responsibilities:    - 不负责数据库连接管理    - 不负责用户权限验证@Input: 原始用户数据 JSON 对象@Output: 格式化后的数据字典或报表文件路径"""
1.2 文件夹索引文档 (folder.md)
每个功能文件夹内必须包含一个 folder.md 文件，用于描述该目录的整体架构。

功能范围: 该文件夹内代码文件共同实现的功能。
边界定义: 该文件夹模块不涉及的职责。
接口定义: 该模块对外的输入与输出接口。
文件清单: 简要说明文件夹内各代码文件的作用。
2. 文档维护机制
实时同步原则：

每次修改代码逻辑、新增函数或删除文件时，必须立即更新对应的文件头注释。
每次在文件夹内新增、删除文件或改变模块职责时，必须立即更新 folder.md。
文档更新是代码提交的一部分，不可遗漏。
3. 代码实现与重构策略
3.1 优先重用原则
在开发新功能或修复 Bug 时，必须遵循以下优先级：

检查现有实现: 在编写新代码前，必须全面搜索项目代码库，确认是否已存在相同或相似的实现。
优先改动: 如果存在相似实现，优先考虑扩展现有函数、抽象公共方法或重构现有代码，而不是创建新文件或复制代码。
避免冗余: 坚决避免重复造轮子，确保代码的 DRY (Don't Repeat Yourself) 特性。
3.2 决策确认机制
在以下场景中，必须暂停编码，提出方案并向用户确认：

发现已有多处相似实现，不确定应复用哪一个。
存在多种技术方案可实现需求，且各有利弊。
预计的重构改动范围较大，可能影响其他模块。
3.3 计划先行流程
执行任何代码修改前，必须遵循“计划-确认-执行”流程：

停止编码: 不要直接开始修改文件。
列出计划: 清晰列出即将执行的修改步骤、涉及的文件及原因。
等待确认: 向用户展示计划，等待用户回复“确认”或“同意”。
执行修改: 获得许可后，方可开始代码编写与文档更新。

## Project Overview

TradingAgents is a multi-agent LLM financial trading framework built with LangGraph. It simulates a trading firm with specialized agents that collaborate to make trading decisions.

## Commands

### Installation
```bash
pip install -r requirements.txt
# Or install as package
pip install -e .
```

### Run CLI
```bash
python -m cli.main
# Or after installation:
tradingagents
```

### Run programmatically
```bash
python main.py
```

### Environment Setup
Copy `.env.example` to `.env` and set API keys for your chosen LLM provider:
- `OPENAI_API_KEY` - OpenAI (GPT)
- `GOOGLE_API_KEY` - Google (Gemini)
- `ANTHROPIC_API_KEY` - Anthropic (Claude)
- `XAI_API_KEY` - xAI (Grok)
- `OPENROUTER_API_KEY` - OpenRouter
- `ALPHA_VANTAGE_API_KEY` - Alpha Vantage (alternative data source)

## Architecture

### Agent Workflow (LangGraph)
The system uses a StateGraph with the following execution flow:

1. **Analyst Team** (parallel/sequential based on config):
   - Market Analyst - technical indicators, price data
   - Social Media Analyst - sentiment analysis
   - News Analyst - news and global events
   - Fundamentals Analyst - financial statements

2. **Research Team**:
   - Bull Researcher ↔ Bear Researcher (debate rounds)
   - Research Manager (judge)

3. **Trader** - synthesizes research into investment plan

4. **Risk Management**:
   - Aggressive ↔ Conservative ↔ Neutral Analysts (discussion)
   - Risk Judge (final decision)

### Key Files

- `tradingagents/graph/trading_graph.py` - Main orchestration class `TradingAgentsGraph`
- `tradingagents/graph/setup.py` - LangGraph workflow definition
- `tradingagents/agents/` - All agent implementations
- `tradingagents/agents/utils/agent_states.py` - State definitions (`AgentState`, `InvestDebateState`, `RiskDebateState`)
- `tradingagents/default_config.py` - Configuration options
- `tradingagents/llm_clients/factory.py` - LLM provider factory
- `tradingagents/dataflows/interface.py` - Data vendor routing

### Configuration

The `DEFAULT_CONFIG` controls:
- `llm_provider` - "openai", "google", "anthropic", "xai", "openrouter", "ollama"
- `deep_think_llm` / `quick_think_llm` - Model names for complex vs simple tasks
- `max_debate_rounds` - Bull/bear debate rounds
- `max_risk_discuss_rounds` - Risk discussion rounds
- `data_vendors` - Data source per category: `yfinance` (default, free) or `alpha_vantage`

### Data Sources

Two data vendors supported with automatic fallback:
- **yfinance**: Free, no API key required (default)
- **Alpha Vantage**: Requires `ALPHA_VANTAGE_API_KEY`

Configure per-category in `data_vendors`:
```python
"data_vendors": {
    "core_stock_apis": "yfinance",
    "technical_indicators": "yfinance",
    "fundamental_data": "yfinance",
    "news_data": "yfinance",
}
```

### LLM Provider Support

Providers are configured via `llm_provider` config key:
- `openai` - GPT models via OpenAI API
- `google` - Gemini models via Google API
- `anthropic` - Claude models via Anthropic API
- `xai` - Grok models via xAI API
- `openrouter` - Multiple models via OpenRouter
- `ollama` - Local models via Ollama
- `dashscope` - Qwen models via Alibaba Cloud Dashscope (中国可用)

Provider-specific options:
- `google_thinking_level` - "high", "minimal", etc.
- `openai_reasoning_effort` - "medium", "high", "low"

### 中国大陆用户配置指南

#### LLM 配置
推荐使用阿里云 Dashscope (通义千问)：
```python
DEFAULT_CONFIG = {
    "llm_provider": "dashscope",
    "deep_think_llm": "qwen3.5-plus",      # 复杂推理任务
    "quick_think_llm": "qwen3-turbo",    # 快速响应任务
}
```
环境变量设置：
```
DASHSCOPE_API_KEY=your_api_key_here
```

#### 数据源替代方案

| 数据类型 | 当前方案 | 中国可用替代 | 状态 |
|---------|---------|-------------|------|
| 股票行情 | yfinance | AKShare / Baostock | 需要集成 |
| 技术指标 | yfinance + stockstats | AKShare / 本地计算 | 需要集成 |
| 基本面数据 | yfinance | AKShare / Tushare | 需要集成 |
| 新闻数据 | yfinance | AKShare / 新浪财经 | 需要集成 |

**推荐的免费数据源:**
1. **AKShare** - 免费、稳定、无需 API Key
   - 支持A股、港股、美股数据
   - 支持技术指标、财务数据
   - 安装: `pip install akshare`

2. **Baostock** - 免费、稳定
   - 主要支持A股数据
   - 安装: `pip install baostock`

3. **Tushare** - 需要注册获取 Token
   - 数据全面但需要积分
   - 安装: `pip install tushare`

**注意:** yfinance 在中国大陆可能需要代理访问，建议使用 AKShare 作为替代。