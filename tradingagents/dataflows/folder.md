# Dataflows 模块

## 功能范围

数据获取和管理模块，负责从多个数据源获取金融数据，支持自动回退和本地缓存。

## 边界定义

- **负责**: 数据获取、缓存管理、供应商路由
- **不负责**: 数据分析逻辑、交易决策、UI 展示

## 接口定义

### 输入接口

- `route_to_vendor(method, *args, **kwargs)` - 统一数据获取入口
- 配置文件 `data_vendors` 和 `tool_vendors` 指定数据源

### 输出接口

- 股票行情数据 (OHLCV)
- 技术指标数据
- 基本面数据 (财务报表)
- 新闻数据

## 文件清单

| 文件 | 职责 |
|------|------|
| `interface.py` | 数据源路由接口，统一入口 |
| `config.py` | 配置管理 |
| `data_cache.py` | 数据缓存管理 (24小时有效期) |
| `akshare_stock.py` | AKShare 股票行情数据 (A股使用腾讯接口) |
| `akshare_fundamentals.py` | AKShare 基本面数据 |
| `akshare_news.py` | AKShare 新闻数据 |
| `y_finance.py` | yfinance 股票数据 |
| `yfinance_news.py` | yfinance 新闻数据 |
| `alpha_vantage.py` | Alpha Vantage 数据入口 |
| `alpha_vantage_stock.py` | Alpha Vantage 股票数据 |
| `alpha_vantage_indicator.py` | Alpha Vantage 技术指标 |
| `alpha_vantage_fundamentals.py` | Alpha Vantage 基本面数据 |
| `alpha_vantage_news.py` | Alpha Vantage 新闻数据 |
| `alpha_vantage_common.py` | Alpha Vantage 公共方法 |
| `stockstats_utils.py` | stockstats 工具类 |
| `utils.py` | 通用工具方法 |

## 数据源说明

### AKShare (推荐中国用户)

- **优点**: 免费、无需 API Key、中国可直接访问
- **支持**: A股、港股、部分美股
- **A股数据源**: 腾讯财经接口 (`stock_zh_a_hist_tx`)，稳定可靠
- **安装**: `pip install akshare`

### yfinance

- **优点**: 美股数据全面
- **缺点**: 中国需要代理访问
- **安装**: `pip install yfinance`

### Alpha Vantage

- **优点**: 数据稳定、API 规范
- **缺点**: 需要 API Key、中国需要代理
- **安装**: 内置

## 缓存机制

- 默认缓存有效期: 24小时
- 缓存位置: `dataflows/data_cache/`
- 降级策略: 无法获取新数据时使用过期缓存

## 使用示例

```python
from tradingagents.dataflows.interface import route_to_vendor

# 获取股票行情
data = route_to_vendor("get_stock_data", "AAPL", "2024-01-01", "2024-12-31")

# 获取技术指标
indicators = route_to_vendor("get_indicators", "AAPL", "rsi", "2024-12-31", 30)

# 获取基本面
fundamentals = route_to_vendor("get_fundamentals", "AAPL", "2024-12-31")
```

## 配置示例

```python
# 默认配置 (default_config.py)
DEFAULT_CONFIG = {
    "data_vendors": {
        "core_stock_apis": "akshare",
        "technical_indicators": "akshare",
        "fundamental_data": "akshare",
        "news_data": "akshare",
    },
    "cache_validity_hours": 24,
}
```