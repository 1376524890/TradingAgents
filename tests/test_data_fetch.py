#!/usr/bin/env python3
"""
@File: test_data_fetch_v2.py
@Contains: [main]
@Responsibilities:
    - 测试股票数据获取功能
    - 验证网络连接和 API 可用性
@Non-Responsibilities:
    - 不测试基本面和新闻数据
@Input: 无
@Output: 测试结果报告
"""

import sys
import os
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta


def test_network():
    """测试基础网络连接"""
    print("\n" + "=" * 60)
    print("【测试 1】基础网络连接测试")
    print("=" * 60)

    import urllib.request

    test_urls = [
        ("百度", "https://www.baidu.com"),
        ("新浪财经", "https://finance.sina.com.cn"),
        ("东方财富", "https://www.eastmoney.com"),
    ]

    results = []
    for name, url in test_urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req, timeout=10)
            status = "OK" if response.status == 200 else f"HTTP {response.status}"
            print(f"  ✓ [{name}] {url} - {status}")
            results.append(True)
        except Exception as e:
            print(f"  ✗ [{name}] {url} - FAILED: {e}")
            results.append(False)

    return all(results)


def test_akshare():
    """测试 AKShare 数据获取"""
    print("\n" + "=" * 60)
    print("【测试 2】AKShare 数据获取测试")
    print("=" * 60)

    try:
        import akshare as ak
        print(f"  AKShare 版本: {ak.__version__}")
    except ImportError:
        print("  ✗ AKShare 未安装")
        return False

    results = []

    # 1. 测试腾讯历史数据接口 (已知可用)
    print("\n  测试腾讯历史数据接口 (stock_zh_a_hist_tx):")
    try:
        df = ak.stock_zh_a_hist_tx(symbol='sz000001')
        if df is not None and not df.empty:
            print(f"    ✓ 成功获取平安银行 {len(df)} 条历史数据")
            print(f"    最新数据: {df.iloc[-1]['date']} 收盘价 {df.iloc[-1]['close']}")
            results.append(True)
        else:
            print("    ✗ 数据为空")
            results.append(False)
    except Exception as e:
        print(f"    ✗ 失败: {e}")
        results.append(False)

    # 2. 测试指数数据
    print("\n  测试指数数据接口 (stock_zh_index_daily):")
    try:
        df = ak.stock_zh_index_daily(symbol='sh000001')
        if df is not None and not df.empty:
            print(f"    ✓ 成功获取上证指数 {len(df)} 条数据")
            print(f"    最新数据: {df.iloc[-1]['date']} 收盘价 {df.iloc[-1]['close']:.2f}")
            results.append(True)
        else:
            print("    ✗ 数据为空")
            results.append(False)
    except Exception as e:
        print(f"    ✗ 失败: {e}")
        results.append(False)

    # 3. 测试外汇数据
    print("\n  测试外汇数据接口 (fx_pair_quote):")
    try:
        df = ak.fx_pair_quote()
        if df is not None and not df.empty:
            print(f"    ✓ 成功获取 {len(df)} 条外汇数据")
            results.append(True)
        else:
            print("    ✗ 数据为空")
            results.append(False)
    except Exception as e:
        print(f"    ✗ 失败: {e}")
        results.append(False)

    return any(results)


def test_yfinance():
    """测试 yfinance 数据获取"""
    print("\n" + "=" * 60)
    print("【测试 3】yfinance 数据获取测试 (可能需要代理)")
    print("=" * 60)

    try:
        import yfinance as yf
        print(f"  yfinance 版本: {yf.__version__}")
    except ImportError:
        print("  ✗ yfinance 未安装")
        return False

    # 测试简单查询
    print("\n  测试获取 AAPL 信息:")
    try:
        ticker = yf.Ticker('AAPL')
        # 使用 Ticker.info 而不是 history 避免 rate limit
        info = ticker.info
        if info:
            price = info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))
            print(f"    ✓ 成功获取 AAPL 信息，当前价格: {price}")
            return True
        else:
            print("    ✗ 信息为空")
            return False
    except Exception as e:
        print(f"    ✗ 失败: {type(e).__name__}: {str(e)[:50]}...")
        return False


def test_stockstats():
    """测试 stockstats 技术指标"""
    print("\n" + "=" * 60)
    print("【测试 4】stockstats 技术指标测试")
    print("=" * 60)

    try:
        import akshare as ak
        from stockstats import StockDataFrame
        import pandas as pd

        print("  获取数据并计算技术指标...")

        # 使用腾讯接口获取数据
        df = ak.stock_zh_a_hist_tx(symbol='sz000001')

        if df is None or df.empty:
            print("  ✗ 无法获取数据")
            return False

        # 重命名列以符合 stockstats 格式
        df = df.rename(columns={
            'date': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'amount': 'Volume'
        })

        # 计算技术指标
        stock_df = StockDataFrame.retype(df.copy())

        # 测试几个常用指标
        indicators = ['rsi', 'macd', 'close_50_sma']
        results = []

        for ind in indicators:
            try:
                values = stock_df[ind]
                last_val = values.iloc[-1]
                if pd.notna(last_val):
                    print(f"    ✓ {ind}: {last_val:.4f}")
                    results.append(True)
                else:
                    print(f"    ⚠ {ind}: N/A (需要更多数据)")
                    results.append(True)  # 不算失败
            except Exception as e:
                print(f"    ✗ {ind}: 计算失败 - {e}")
                results.append(False)

        return all(results)

    except ImportError as e:
        print(f"  ✗ 缺少依赖: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("TradingAgents 数据获取功能测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    # 运行测试
    results["网络连接"] = test_network()
    results["AKShare数据"] = test_akshare()
    results["yfinance数据"] = test_yfinance()
    results["技术指标"] = test_stockstats()

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {status} - {name}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    print(f"\n  总计: {passed}/{total} 通过")

    # 建议
    print("\n" + "=" * 60)
    print("诊断建议")
    print("=" * 60)

    if results["AKShare数据"]:
        print("  ✓ AKShare 数据源可用，建议使用 akshare 作为主要数据源")
    else:
        print("  ✗ AKShare 数据源不可用，请检查网络或安装最新版本: pip install akshare --upgrade")

    if results["yfinance数据"]:
        print("  ✓ yfinance 数据源可用")
    else:
        print("  ⚠ yfinance 在中国大陆可能需要代理才能访问")

    if passed >= 3:
        print("\n  ✓ 系统数据获取功能正常，可以正常使用")
        return 0
    elif passed >= 2:
        print("\n  ⚠ 部分功能正常，建议检查失败的模块")
        return 1
    else:
        print("\n  ✗ 多数测试失败，请检查网络连接和依赖安装")
        return 2


if __name__ == "__main__":
    sys.exit(main())