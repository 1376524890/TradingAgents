"""@File: akshare_stock.py
@Contains: [get_stock_data_akshare, get_indicators_akshare, _convert_to_tencent_symbol]
@Responsibilities:
    - 从 AKShare 获取股票行情数据 (OHLCV)
    - A股数据使用腾讯接口 (stock_zh_a_hist_tx)
    - 计算技术指标
    - 实现缓存机制和降级策略
@Non-Responsibilities:
    - 不负责基本面数据获取
    - 不负责新闻数据获取
@Input: 股票代码、日期范围、指标名称
@Output: 格式化的股票数据字符串
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Annotated, Optional, Dict
from dateutil.relativedelta import relativedelta

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("[Warning] AKShare not installed. Run: pip install akshare")

# 网络重试配置
import time
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def _retry_akshare_call(func, *args, **kwargs):
    """带重试的 AKShare API 调用"""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                print(f"[Retry] AKShare API call failed, retrying ({attempt + 1}/{MAX_RETRIES}): {e}")
    raise last_error

from .data_cache import get_cache, make_cache_key


def _convert_ticker_for_akshare(ticker: str) -> str:
    """
    将股票代码转换为 AKShare 格式。

    AKShare 使用带市场前缀的格式，如：
    - 美股: AAPL (保持不变，但需要使用美股接口)
    - A股: 000001 -> 000001 (深市), 600000 -> 600000 (沪市)
    - 港股: 00700 -> 00700

    Args:
        ticker: 原始股票代码

    Returns:
        AKShare 格式的股票代码
    """
    ticker = ticker.upper().strip()

    # 判断是否为美股（纯字母或含点号）
    if ticker.isalpha() or ('.' in ticker and not ticker.startswith('0') and not ticker.startswith('6')):
        return ticker  # 美股保持原样

    # A股/港股数字代码处理
    if ticker.isdigit():
        # 补齐到6位
        ticker = ticker.zfill(6)

        # 判断市场
        if ticker.startswith('6'):
            return ticker  # 沪市
        elif ticker.startswith('0') or ticker.startswith('3'):
            return ticker  # 深市
        elif ticker.startswith('1') or ticker.startswith('5'):
            return ticker  # 基金/债券
        else:
            return ticker  # 港股或其他

    return ticker


def _is_china_stock(ticker: str) -> bool:
    """判断是否为中国A股或港股。"""
    ticker = ticker.upper().strip()
    if ticker.isdigit():
        ticker = ticker.zfill(6)
        # A股: 00/30开头(深市), 60开头(沪市)
        # 港股: 0开头(但不是00/30/60)
        return ticker.startswith(('0', '3', '6'))
    return False


def _is_us_stock(ticker: str) -> bool:
    """判断是否为美股。"""
    ticker = ticker.upper().strip()
    return ticker.isalpha() or ('.' in ticker and not _is_china_stock(ticker))


def _convert_to_tencent_symbol(ticker: str) -> str:
    """
    将股票代码转换为腾讯接口格式 (带市场前缀)。

    腾讯接口需要格式如:
    - 沪市: sh600000
    - 深市: sz000001, sz300001

    Args:
        ticker: 原始股票代码

    Returns:
        腾讯接口格式的股票代码
    """
    ticker = ticker.upper().strip().zfill(6)
    if ticker.startswith('6'):
        return f"sh{ticker}"  # 沪市
    elif ticker.startswith(('0', '3')):
        return f"sz{ticker}"  # 深市
    return ticker


def get_stock_data_akshare(
    symbol: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    从 AKShare 获取股票行情数据。

    支持:
    - A股 (沪深)
    - 港股
    - 美股

    Args:
        symbol: 股票代码
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)

    Returns:
        格式化的股票行情数据字符串
    """
    if not AKSHARE_AVAILABLE:
        return f"[Error] AKShare not installed. Cannot fetch data for {symbol}"

    cache = get_cache()
    cache_key = make_cache_key("stock_data", symbol, start_date, end_date)

    # 尝试从缓存获取
    cached = cache.get(cache_key, allow_expired=True)
    if cached and not cached.get("is_expired", False):
        return cached["data"]
    elif cached:
        print(f"[Cache] Using expired cache for {symbol} (age: {cached.get('cache_age_hours', 0):.1f}h)")

    try:
        # 解析日期
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        # 转换股票代码格式
        akshare_symbol = _convert_ticker_for_akshare(symbol)

        # 根据股票类型选择接口
        if _is_china_stock(symbol):
            # A股数据 - 使用腾讯接口 (更稳定)
            tencent_symbol = _convert_to_tencent_symbol(symbol)
            df = _retry_akshare_call(
                ak.stock_zh_a_hist_tx,
                symbol=tencent_symbol,
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust="qfq"  # 前复权
            )
            # 腾讯接口列名已是英文，只需重命名 amount -> Volume
            if df is not None and not df.empty:
                df = df.rename(columns={"amount": "Volume"})
                df["Adj Close"] = df["Close"]  # A股复权后价格

        elif _is_us_stock(symbol):
            # 美股数据
            df = ak.stock_us_hist(symbol=symbol, period="daily", adjust="qfq")
            if df is not None and not df.empty:
                df = df.rename(columns={
                    "日期": "Date",
                    "开盘": "Open",
                    "最高": "High",
                    "最低": "Low",
                    "收盘": "Close",
                    "成交量": "Volume"
                })
                df["Adj Close"] = df["Close"]

        else:
            # 港股数据
            df = ak.stock_hk_hist(
                symbol=akshare_symbol,
                period="daily",
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust="qfq"
            )
            if df is not None and not df.empty:
                df = df.rename(columns={
                    "日期": "Date",
                    "开盘": "Open",
                    "最高": "High",
                    "最低": "Low",
                    "收盘": "Close",
                    "成交量": "Volume"
                })
                df["Adj Close"] = df["Close"]

        if df is None or df.empty:
            # 尝试使用过期缓存
            if cached:
                return cached["data"]
            return f"No data found for symbol '{symbol}' between {start_date} and {end_date}"

        # 确保日期列格式正确
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

        # 选择需要的列
        columns_to_keep = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
        available_cols = [col for col in columns_to_keep if col in df.columns]
        df = df[available_cols]

        # 数值保留两位小数
        numeric_cols = ["Open", "High", "Low", "Close", "Adj Close"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].round(2)

        # 转换为CSV格式
        csv_string = df.to_csv(index=False)

        # 添加头部信息
        header = f"# Stock data for {symbol.upper()}\n"
        header += f"# Source: AKShare\n"
        header += f"# Date range: {start_date} to {end_date}\n"
        header += f"# Total records: {len(df)}\n"
        header += f"# Retrieved at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        result = header + csv_string

        # 缓存结果
        cache.set(cache_key, result, {"symbol": symbol, "start": start_date, "end": end_date})

        return result

    except Exception as e:
        # 尝试使用过期缓存
        if cached:
            print(f"[Cache] API error, using expired cache: {e}")
            return cached["data"]
        return f"Error fetching stock data for {symbol}: {str(e)}"


def get_indicators_akshare(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator to get the analysis and report of"],
    curr_date: Annotated[str, "The current trading date, YYYY-mm-dd"],
    look_back_days: Annotated[int, "how many days to look back"] = 30,
) -> str:
    """
    计算技术指标。

    从 AKShare 获取股票数据后使用 stockstats 计算技术指标。

    支持的指标:
    - close_50_sma: 50日简单移动平均
    - close_200_sma: 200日简单移动平均
    - close_10_ema: 10日指数移动平均
    - macd: MACD指标
    - macds: MACD信号线
    - macdh: MACD柱状图
    - rsi: 相对强弱指标
    - boll: 布林带中轨
    - boll_ub: 布林带上轨
    - boll_lb: 布林带下轨
    - atr: 平均真实波幅
    - vwma: 成交量加权移动平均
    - mfi: 资金流量指标

    Args:
        symbol: 股票代码
        indicator: 技术指标名称
        curr_date: 当前日期
        look_back_days: 回溯天数

    Returns:
        格式化的技术指标数据字符串
    """
    if not AKSHARE_AVAILABLE:
        return f"[Error] AKShare not installed. Cannot calculate indicators for {symbol}"

    from stockstats import StockDataFrame

    cache = get_cache()
    cache_key = make_cache_key("indicators", symbol, indicator, curr_date, look_back_days)

    # 尝试从缓存获取
    cached = cache.get(cache_key, allow_expired=True)
    if cached and not cached.get("is_expired", False):
        return cached["data"]
    elif cached:
        print(f"[Cache] Using expired cache for indicators {symbol}/{indicator}")

    # 指标说明
    INDICATOR_DESCRIPTIONS = {
        "close_50_sma": "50 SMA: A medium-term trend indicator. Usage: Identify trend direction and serve as dynamic support/resistance.",
        "close_200_sma": "200 SMA: A long-term trend benchmark. Usage: Confirm overall market trend and identify golden/death cross setups.",
        "close_10_ema": "10 EMA: A responsive short-term average. Usage: Capture quick shifts in momentum and potential entry points.",
        "macd": "MACD: Computes momentum via differences of EMAs. Usage: Look for crossovers and divergence as signals of trend changes.",
        "macds": "MACD Signal: An EMA smoothing of the MACD line. Usage: Use crossovers with the MACD line to trigger trades.",
        "macdh": "MACD Histogram: Shows the gap between the MACD line and its signal. Usage: Visualize momentum strength.",
        "rsi": "RSI: Measures momentum to flag overbought/oversold conditions. Usage: Apply 70/30 thresholds.",
        "boll": "Bollinger Middle: A 20 SMA serving as the basis for Bollinger Bands. Usage: Acts as a dynamic benchmark.",
        "boll_ub": "Bollinger Upper Band: Typically 2 standard deviations above the middle line. Usage: Signals potential overbought conditions.",
        "boll_lb": "Bollinger Lower Band: Typically 2 standard deviations below the middle line. Usage: Indicates potential oversold conditions.",
        "atr": "ATR: Averages true range to measure volatility. Usage: Set stop-loss levels and adjust position sizes.",
        "vwma": "VWMA: A moving average weighted by volume. Usage: Confirm trends by integrating price action with volume data.",
        "mfi": "MFI: The Money Flow Index uses both price and volume to measure buying and selling pressure. Usage: Identify overbought/oversold conditions.",
    }

    if indicator not in INDICATOR_DESCRIPTIONS:
        return f"Indicator '{indicator}' not supported. Available: {list(INDICATOR_DESCRIPTIONS.keys())}"

    try:
        # 计算需要的日期范围（需要更多历史数据来计算指标）
        curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
        # 需要额外数据来计算指标（如200日均线需要至少200天数据）
        extra_days = max(look_back_days, 250)
        start_dt = curr_dt - timedelta(days=extra_days)
        start_date = start_dt.strftime("%Y-%m-%d")
        end_date = curr_date

        # 获取股票数据
        stock_data_str = get_stock_data_akshare(symbol, start_date, end_date)

        if stock_data_str.startswith("Error") or stock_data_str.startswith("No data"):
            if cached:
                return cached["data"]
            return stock_data_str

        # 解析CSV数据
        from io import StringIO
        lines = stock_data_str.split('\n')
        # 跳过注释行
        csv_lines = [l for l in lines if not l.startswith('#') and l.strip()]
        csv_data = '\n'.join(csv_lines)

        df = pd.read_csv(StringIO(csv_data))

        if df.empty:
            if cached:
                return cached["data"]
            return f"No data available to calculate {indicator}"

        # 使用 stockstats 计算指标
        stock_df = StockDataFrame.retype(df.copy())

        try:
            indicator_values = stock_df[indicator]
        except Exception as e:
            if cached:
                return cached["data"]
            return f"Error calculating indicator {indicator}: {str(e)}"

        # 构建输出
        before_dt = curr_dt - timedelta(days=look_back_days)
        result_lines = [f"## {indicator} values from {before_dt.strftime('%Y-%m-%d')} to {curr_date}:\n"]

        # 获取最近 look_back_days 天的指标值
        date_col = "Date" if "Date" in df.columns else df.columns[0]
        result_count = 0

        for i in range(len(df) - 1, -1, -1):
            if result_count >= look_back_days:
                break

            try:
                date_val = df[date_col].iloc[i]
                ind_val = indicator_values.iloc[i]

                if pd.notna(ind_val):
                    result_lines.append(f"{date_val}: {ind_val:.4f}")
                else:
                    result_lines.append(f"{date_val}: N/A (insufficient data)")

                result_count += 1
            except (IndexError, KeyError):
                continue

        result_lines.append("\n")
        result_lines.append(INDICATOR_DESCRIPTIONS.get(indicator, "No description available."))

        result = '\n'.join(result_lines)

        # 缓存结果
        cache.set(cache_key, result, {
            "symbol": symbol,
            "indicator": indicator,
            "curr_date": curr_date
        })

        return result

    except Exception as e:
        if cached:
            print(f"[Cache] Error calculating indicators, using cache: {e}")
            return cached["data"]
        return f"Error calculating indicators for {symbol}: {str(e)}"