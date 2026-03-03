"""@File: akshare_news.py
@Contains: [get_news_akshare, get_global_news_akshare]
@Responsibilities:
    - 从 AKShare 获取新闻数据
    - 获取公司相关新闻
    - 获取宏观经济/市场新闻
@Non-Responsibilities:
    - 不负责股票行情数据
    - 不负责基本面数据
@Input: 股票代码、日期范围
@Output: 格式化的新闻数据字符串
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Annotated, Optional, List
from dateutil.relativedelta import relativedelta

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("[Warning] AKShare not installed. Run: pip install akshare")

from .data_cache import get_cache, make_cache_key
from .akshare_stock import _is_china_stock, _is_us_stock


def get_news_akshare(
    ticker: Annotated[str, "Ticker symbol"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    获取公司相关新闻。

    Args:
        ticker: 股票代码
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        格式化的新闻数据字符串
    """
    if not AKSHARE_AVAILABLE:
        return f"[Error] AKShare not installed. Cannot fetch news for {ticker}"

    cache = get_cache()
    cache_key = make_cache_key("news", ticker, start_date, end_date)

    cached = cache.get(cache_key, allow_expired=True)
    if cached and not cached.get("is_expired", False):
        return cached["data"]
    elif cached:
        print(f"[Cache] Using expired cache for news {ticker}")

    try:
        result_lines = []
        result_lines.append(f"## {ticker} News, from {start_date} to {end_date}:\n")

        # 解析日期
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        news_count = 0

        if _is_china_stock(ticker):
            # A股新闻 - 使用东方财富新闻接口
            try:
                # 获取个股新闻
                df = ak.stock_news_em(symbol=ticker)

                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        if news_count >= 15:  # 限制新闻数量
                            break

                        # 尝试解析发布时间
                        pub_time = row.get('发布时间', row.get('time', ''))
                        title = row.get('新闻标题', row.get('title', '无标题'))
                        content = row.get('新闻内容', row.get('content', ''))
                        source = row.get('来源', row.get('source', '未知来源'))

                        # 日期过滤
                        if pub_time:
                            try:
                                pub_dt = datetime.strptime(str(pub_time)[:10], "%Y-%m-%d")
                                if not (start_dt <= pub_dt <= end_dt + timedelta(days=1)):
                                    continue
                            except ValueError:
                                pass

                        result_lines.append(f"### {title}")
                        result_lines.append(f"来源: {source}")
                        if pub_time:
                            result_lines.append(f"时间: {pub_time}")
                        if content and len(content) > 20:
                            # 截取摘要
                            summary = content[:300] + "..." if len(content) > 300 else content
                            result_lines.append(f"摘要: {summary}")
                        result_lines.append("")
                        news_count += 1

            except Exception as e:
                result_lines.append(f"[Warning] Could not fetch stock-specific news: {e}")

        else:
            # 美股/港股新闻 - 使用财经新闻接口
            try:
                # 获取财经新闻
                df = ak.stock_news_em(symbol="财经新闻")

                if df is not None and not df.empty:
                    # 搜索相关新闻
                    ticker_upper = ticker.upper()
                    for _, row in df.iterrows():
                        if news_count >= 10:
                            break

                        title = row.get('新闻标题', row.get('title', ''))
                        content = row.get('新闻内容', row.get('content', ''))

                        # 简单关键词匹配
                        if ticker_upper in title.upper() or ticker_upper in content.upper():
                            result_lines.append(f"### {title}")
                            source = row.get('来源', row.get('source', '未知'))
                            result_lines.append(f"来源: {source}")
                            if content and len(content) > 20:
                                summary = content[:300] + "..." if len(content) > 300 else content
                                result_lines.append(f"摘要: {summary}")
                            result_lines.append("")
                            news_count += 1

            except Exception as e:
                result_lines.append(f"[Warning] Could not fetch financial news: {e}")

        if news_count == 0:
            result_lines.append(f"No news found for {ticker} between {start_date} and {end_date}")
            result_lines.append("\n[提示] 可尝试:")
            result_lines.append("1. 扩大日期范围")
            result_lines.append("2. 使用其他新闻源 (配置代理访问 yfinance)")

        result = '\n'.join(result_lines)

        # 缓存结果
        cache.set(cache_key, result, {"ticker": ticker, "start": start_date, "end": end_date})

        return result

    except Exception as e:
        if cached:
            print(f"[Cache] API error, using expired cache: {e}")
            return cached["data"]
        return f"Error fetching news for {ticker}: {str(e)}"


def get_global_news_akshare(
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "Number of days to look back"] = 7,
    limit: Annotated[int, "Maximum number of articles to return"] = 10,
) -> str:
    """
    获取全球/宏观经济新闻。

    Args:
        curr_date: 当前日期
        look_back_days: 回溯天数
        limit: 最大文章数

    Returns:
        格式化的新闻数据字符串
    """
    if not AKSHARE_AVAILABLE:
        return "[Error] AKShare not installed. Cannot fetch global news"

    cache = get_cache()
    cache_key = make_cache_key("global_news", curr_date, look_back_days, limit)

    cached = cache.get(cache_key, allow_expired=True)
    if cached and not cached.get("is_expired", False):
        return cached["data"]
    elif cached:
        print(f"[Cache] Using expired cache for global news")

    try:
        # 计算日期范围
        curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
        start_dt = curr_dt - timedelta(days=look_back_days)
        start_date = start_dt.strftime("%Y-%m-%d")

        result_lines = []
        result_lines.append(f"## Global Market News, from {start_date} to {curr_date}:\n")

        news_items = []

        # 尝试多个新闻源
        news_sources = [
            ("财经新闻", "stock_news_em"),
            ("股票新闻", "stock_news_em"),
        ]

        for source_name, api_func in news_sources:
            try:
                df = getattr(ak, api_func)(symbol=source_name)

                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        title = row.get('新闻标题', row.get('title', '无标题'))
                        content = row.get('新闻内容', row.get('content', ''))
                        pub_time = row.get('发布时间', row.get('time', ''))
                        source = row.get('来源', row.get('source', source_name))

                        news_items.append({
                            'title': title,
                            'content': content,
                            'time': pub_time,
                            'source': source
                        })

            except Exception as e:
                continue

        # 去重并按时间排序
        seen_titles = set()
        unique_news = []
        for item in news_items:
            if item['title'] not in seen_titles:
                seen_titles.add(item['title'])
                unique_news.append(item)

        # 输出新闻
        for i, item in enumerate(unique_news[:limit]):
            result_lines.append(f"### {item['title']}")
            result_lines.append(f"来源: {item['source']}")
            if item['time']:
                result_lines.append(f"时间: {item['time']}")
            if item['content'] and len(item['content']) > 20:
                summary = item['content'][:300] + "..." if len(item['content']) > 300 else item['content']
                result_lines.append(f"摘要: {summary}")
            result_lines.append("")

        if not unique_news:
            result_lines.append("No global news found for the specified period")
            result_lines.append("\n[提示] 可尝试:")
            result_lines.append("1. 增加 look_back_days 参数")
            result_lines.append("2. 使用其他新闻源")

        result = '\n'.join(result_lines)

        # 缓存结果
        cache.set(cache_key, result, {"curr_date": curr_date, "look_back_days": look_back_days})

        return result

    except Exception as e:
        if cached:
            print(f"[Cache] API error, using expired cache: {e}")
            return cached["data"]
        return f"Error fetching global news: {str(e)}"