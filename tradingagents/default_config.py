"""@File: default_config.py
@Contains: [DEFAULT_CONFIG]
@Responsibilities:
    - 定义项目默认配置
    - 配置 LLM 提供商和模型
    - 配置数据源供应商
@Non-Responsibilities:
    - 不负责配置的动态修改
    - 不负责环境变量读取
@Input: 无
@Output: DEFAULT_CONFIG 字典
"""

import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings
    "llm_provider": "dashscope",
    "deep_think_llm": "qwen3.5-plus",
    "quick_think_llm": "qwen3.5-flash",
    "backend_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    # Provider-specific thinking configuration
    "google_thinking_level": None,      # "high", "minimal", etc.
    "openai_reasoning_effort": None,    # "medium", "high", "low"
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Data vendor configuration
    # Category-level configuration (default for all tools in category)
    # Options: akshare (China-accessible), yfinance (requires proxy), alpha_vantage (requires API key)
    "data_vendors": {
        "core_stock_apis": "akshare",       # akshare recommended for Chinese users
        "technical_indicators": "akshare",  # akshare uses stockstats for indicators
        "fundamental_data": "akshare",      # akshare for A-shares fundamentals
        "news_data": "akshare",             # akshare for financial news
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # Example: "get_stock_data": "yfinance",  # Override category default
        # Fallback chain example: "akshare,yfinance" (try akshare first, then yfinance)
    },
    # Cache settings
    "cache_validity_hours": 24,  # Data cache validity period in hours
}
