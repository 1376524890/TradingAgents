"""@File: akshare_fundamentals.py
@Contains: [get_fundamentals_akshare, get_balance_sheet_akshare, get_cashflow_akshare, get_income_statement_akshare, get_insider_transactions_akshare]
@Responsibilities:
    - 从 AKShare 获取基本面数据
    - 获取财务报表 (资产负债表、现金流量表、利润表)
    - 获取公司概况信息
@Non-Responsibilities:
    - 不负责股票行情数据
    - 不负责新闻数据
@Input: 股票代码
@Output: 格式化的财务数据字符串
"""

import os
import pandas as pd
from datetime import datetime
from typing import Annotated, Optional

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("[Warning] AKShare not installed. Run: pip install akshare")

from .data_cache import get_cache, make_cache_key
from .akshare_stock import _is_china_stock, _is_us_stock, _convert_ticker_for_akshare


def get_fundamentals_akshare(
    ticker: Annotated[str, "ticker symbol of the company"],
    curr_date: Annotated[str, "current date (not used for akshare)"] = None
) -> str:
    """
    获取公司基本面概览数据。

    支持 A股 和部分美股。

    Args:
        ticker: 股票代码
        curr_date: 当前日期 (未使用)

    Returns:
        格式化的基本面数据字符串
    """
    if not AKSHARE_AVAILABLE:
        return f"[Error] AKShare not installed. Cannot fetch fundamentals for {ticker}"

    cache = get_cache()
    cache_key = make_cache_key("fundamentals", ticker)

    cached = cache.get(cache_key, allow_expired=True)
    if cached and not cached.get("is_expired", False):
        return cached["data"]
    elif cached:
        print(f"[Cache] Using expired cache for fundamentals {ticker}")

    try:
        result_lines = []
        result_lines.append(f"# Company Fundamentals for {ticker.upper()}")
        result_lines.append(f"# Source: AKShare")
        result_lines.append(f"# Retrieved at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        if _is_china_stock(ticker):
            # A股基本面数据
            akshare_symbol = _convert_ticker_for_akshare(ticker)

            try:
                # 获取公司概况
                profile = ak.stock_individual_info_em(symbol=akshare_symbol)
                if profile is not None and not profile.empty:
                    result_lines.append("## 公司概况\n")
                    for _, row in profile.iterrows():
                        result_lines.append(f"{row['item']}: {row['value']}")
                    result_lines.append("")
            except Exception as e:
                result_lines.append(f"[Warning] Could not fetch company profile: {e}\n")

            try:
                # 获取关键财务指标
                indicators = ak.stock_financial_analysis_indicator(symbol=akshare_symbol)
                if indicators is not None and not indicators.empty:
                    result_lines.append("## 关键财务指标 (最近报告期)\n")
                    # 取最近一行数据
                    latest = indicators.iloc[0] if len(indicators) > 0 else None
                    if latest is not None:
                        for col in indicators.columns:
                            val = latest[col]
                            if pd.notna(val):
                                result_lines.append(f"{col}: {val}")
            except Exception as e:
                result_lines.append(f"[Warning] Could not fetch financial indicators: {e}")

        elif _is_us_stock(ticker):
            # 美股基本面 - AKShare 对美股支持有限
            result_lines.append("## 美股基本面数据\n")
            result_lines.append(f"股票代码: {ticker}")
            result_lines.append("\n[Note] AKShare 对美股基本面数据支持有限，建议使用其他数据源或配置代理访问 yfinance")
            result_lines.append("\n可尝试的替代方案:")
            result_lines.append("1. 使用 yfinance + 代理")
            result_lines.append("2. 使用 Alpha Vantage API")
            result_lines.append("3. 使用 OpenRouter 等聚合数据源")

        else:
            # 港股
            result_lines.append(f"股票代码: {ticker}")
            result_lines.append("\n[Note] 港股基本面数据请参考相关港股数据接口")

        result = '\n'.join(result_lines)

        # 缓存结果
        cache.set(cache_key, result, {"ticker": ticker})

        return result

    except Exception as e:
        if cached:
            print(f"[Cache] API error, using expired cache: {e}")
            return cached["data"]
        return f"Error retrieving fundamentals for {ticker}: {str(e)}"


def get_balance_sheet_akshare(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency of data: 'annual' or 'quarterly'"] = "quarterly",
    curr_date: Annotated[str, "current date (not used for akshare)"] = None
) -> str:
    """
    获取资产负债表数据。

    Args:
        ticker: 股票代码
        freq: 报告频率 ('annual' 或 'quarterly')
        curr_date: 当前日期 (未使用)

    Returns:
        格式化的资产负债表字符串
    """
    if not AKSHARE_AVAILABLE:
        return f"[Error] AKShare not installed. Cannot fetch balance sheet for {ticker}"

    cache = get_cache()
    cache_key = make_cache_key("balance_sheet", ticker, freq)

    cached = cache.get(cache_key, allow_expired=True)
    if cached and not cached.get("is_expired", False):
        return cached["data"]
    elif cached:
        print(f"[Cache] Using expired cache for balance sheet {ticker}")

    try:
        if not _is_china_stock(ticker):
            if cached:
                return cached["data"]
            return f"[Note] Balance sheet data for {ticker} not available via AKShare. Consider using yfinance with proxy."

        akshare_symbol = _convert_ticker_for_akshare(ticker)

        # 获取资产负债表
        df = ak.stock_balance_sheet_by_report_em(symbol=akshare_symbol)

        if df is None or df.empty:
            if cached:
                return cached["data"]
            return f"No balance sheet data found for symbol '{ticker}'"

        # 根据频率筛选
        if freq.lower() == "quarterly":
            # 筛选季报数据
            df = df[df['报告期'].str.contains('季报|三季报|半年报', na=False)].head(8)
        else:
            # 筛选年报数据
            df = df[df['报告期'].str.contains('年报', na=False)].head(5)

        csv_string = df.to_csv(index=False)

        header = f"# Balance Sheet data for {ticker.upper()} ({freq})\n"
        header += f"# Source: AKShare\n"
        header += f"# Retrieved at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        result = header + csv_string

        cache.set(cache_key, result, {"ticker": ticker, "freq": freq})

        return result

    except Exception as e:
        if cached:
            print(f"[Cache] API error, using expired cache: {e}")
            return cached["data"]
        return f"Error retrieving balance sheet for {ticker}: {str(e)}"


def get_cashflow_akshare(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency of data: 'annual' or 'quarterly'"] = "quarterly",
    curr_date: Annotated[str, "current date (not used for akshare)"] = None
) -> str:
    """
    获取现金流量表数据。

    Args:
        ticker: 股票代码
        freq: 报告频率
        curr_date: 当前日期 (未使用)

    Returns:
        格式化的现金流量表字符串
    """
    if not AKSHARE_AVAILABLE:
        return f"[Error] AKShare not installed. Cannot fetch cashflow for {ticker}"

    cache = get_cache()
    cache_key = make_cache_key("cashflow", ticker, freq)

    cached = cache.get(cache_key, allow_expired=True)
    if cached and not cached.get("is_expired", False):
        return cached["data"]
    elif cached:
        print(f"[Cache] Using expired cache for cashflow {ticker}")

    try:
        if not _is_china_stock(ticker):
            if cached:
                return cached["data"]
            return f"[Note] Cashflow data for {ticker} not available via AKShare. Consider using yfinance with proxy."

        akshare_symbol = _convert_ticker_for_akshare(ticker)

        # 获取现金流量表
        df = ak.stock_cash_flow_sheet_by_report_em(symbol=akshare_symbol)

        if df is None or df.empty:
            if cached:
                return cached["data"]
            return f"No cashflow data found for symbol '{ticker}'"

        # 根据频率筛选
        if freq.lower() == "quarterly":
            df = df[df['报告期'].str.contains('季报|三季报|半年报', na=False)].head(8)
        else:
            df = df[df['报告期'].str.contains('年报', na=False)].head(5)

        csv_string = df.to_csv(index=False)

        header = f"# Cash Flow data for {ticker.upper()} ({freq})\n"
        header += f"# Source: AKShare\n"
        header += f"# Retrieved at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        result = header + csv_string

        cache.set(cache_key, result, {"ticker": ticker, "freq": freq})

        return result

    except Exception as e:
        if cached:
            print(f"[Cache] API error, using expired cache: {e}")
            return cached["data"]
        return f"Error retrieving cashflow for {ticker}: {str(e)}"


def get_income_statement_akshare(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency of data: 'annual' or 'quarterly'"] = "quarterly",
    curr_date: Annotated[str, "current date (not used for akshare)"] = None
) -> str:
    """
    获取利润表数据。

    Args:
        ticker: 股票代码
        freq: 报告频率
        curr_date: 当前日期 (未使用)

    Returns:
        格式化的利润表字符串
    """
    if not AKSHARE_AVAILABLE:
        return f"[Error] AKShare not installed. Cannot fetch income statement for {ticker}"

    cache = get_cache()
    cache_key = make_cache_key("income_statement", ticker, freq)

    cached = cache.get(cache_key, allow_expired=True)
    if cached and not cached.get("is_expired", False):
        return cached["data"]
    elif cached:
        print(f"[Cache] Using expired cache for income statement {ticker}")

    try:
        if not _is_china_stock(ticker):
            if cached:
                return cached["data"]
            return f"[Note] Income statement data for {ticker} not available via AKShare. Consider using yfinance with proxy."

        akshare_symbol = _convert_ticker_for_akshare(ticker)

        # 获取利润表
        df = ak.stock_profit_sheet_by_report_em(symbol=akshare_symbol)

        if df is None or df.empty:
            if cached:
                return cached["data"]
            return f"No income statement data found for symbol '{ticker}'"

        # 根据频率筛选
        if freq.lower() == "quarterly":
            df = df[df['报告期'].str.contains('季报|三季报|半年报', na=False)].head(8)
        else:
            df = df[df['报告期'].str.contains('年报', na=False)].head(5)

        csv_string = df.to_csv(index=False)

        header = f"# Income Statement data for {ticker.upper()} ({freq})\n"
        header += f"# Source: AKShare\n"
        header += f"# Retrieved at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        result = header + csv_string

        cache.set(cache_key, result, {"ticker": ticker, "freq": freq})

        return result

    except Exception as e:
        if cached:
            print(f"[Cache] API error, using expired cache: {e}")
            return cached["data"]
        return f"Error retrieving income statement for {ticker}: {str(e)}"


def get_insider_transactions_akshare(
    ticker: Annotated[str, "ticker symbol of the company"]
) -> str:
    """
    获取内部交易数据。

    注意: AKShare 对内部交易数据支持有限，此函数主要返回提示信息。

    Args:
        ticker: 股票代码

    Returns:
        内部交易信息字符串
    """
    cache = get_cache()
    cache_key = make_cache_key("insider_transactions", ticker)

    cached = cache.get(cache_key, allow_expired=True)
    if cached and not cached.get("is_expired", False):
        return cached["data"]

    # AKShare 对内部交易支持有限
    result = f"# Insider Transactions for {ticker.upper()}\n"
    result += f"# Retrieved at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    result += "[Note] AKShare has limited support for insider transaction data.\n"
    result += "For comprehensive insider data, consider:\n"
    result += "1. Using yfinance with proxy\n"
    result += "2. Using Alpha Vantage API\n"
    result += "3. Using Tushare (requires token)\n"

    if _is_china_stock(ticker):
        result += f"\nFor A-shares ({ticker}), you may check:\n"
        result += "- 东方财富网高管交易页面\n"
        result += "- 同花顺财经\n"

    cache.set(cache_key, result, {"ticker": ticker})

    return result