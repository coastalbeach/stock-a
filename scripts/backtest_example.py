# -*- coding: utf-8 -*-
"""
回测系统使用示例

展示如何使用回测系统对策略进行回测和性能评估
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import logging

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入回测模块
from scripts.backtest import BacktestEngine, load_stock_data
from core.strategy.strategy_factory import strategy_factory
from utils.logger import LoggerManager

# 获取日志记录器
logger_manager = LoggerManager()
logger = logger_manager.get_logger('backtest_example')


def run_ma_cross_backtest():
    """
    运行均线交叉策略回测示例
    """
    print("\n运行均线交叉策略回测示例")
    
    # 设置回测参数
    stock_code = '000001'  # 平安银行
    start_date = '2020-01-01'
    end_date = '2020-12-31'
    initial_capital = 100000.0
    
    # 创建回测引擎
    engine = BacktestEngine()
    
    # 加载股票数据
    data = load_stock_data(stock_code, start_date, end_date)
    if data.empty:
        print(f"无法获取股票数据: {stock_code}")
        return
    
    # 添加数据源
    engine.add_data(data, name=stock_code)
    
    # 准备策略参数
    strategy_params = {
        '股票代码': stock_code,
        '开始日期': start_date,
        '结束日期': end_date,
        '初始资金': initial_capital,
        '短期均线': 5,
        '长期均线': 20
    }
    
    # 添加策略
    engine.add_strategy('均线交叉策略', strategy_params)
    
    # 添加分析器
    engine.add_analyzer()
    
    # 设置初始资金
    engine.cerebro.broker.setcash(initial_capital)
    
    # 运行回测
    results = engine.run()
    
    # 分析结果
    analysis = engine.analyze_results(results)
    
    # 打印分析结果
    engine.print_analysis(analysis)
    
    # 保存结果
    engine.save_results(analysis, 'ma_cross_backtest')
    
    # 绘制结果
    engine.plot(results, filename='ma_cross_backtest_plot.png')


def run_macd_backtest():
    """
    运行MACD策略回测示例
    """
    print("\n运行MACD策略回测示例")
    
    # 设置回测参数
    stock_code = '600519'  # 贵州茅台
    start_date = '2020-01-01'
    end_date = '2020-12-31'
    initial_capital = 100000.0
    
    # 创建回测引擎
    engine = BacktestEngine()
    
    # 加载股票数据
    data = load_stock_data(stock_code, start_date, end_date)
    if data.empty:
        print(f"无法获取股票数据: {stock_code}")
        return
    
    # 添加数据源
    engine.add_data(data, name=stock_code)
    
    # 准备策略参数
    strategy_params = {
        '股票代码': stock_code,
        '开始日期': start_date,
        '结束日期': end_date,
        '初始资金': initial_capital,
        'MACD快线': 12,
        'MACD慢线': 26,
        'MACD信号线': 9
    }
    
    # 添加策略
    engine.add_strategy('MACD策略', strategy_params)
    
    # 添加分析器
    engine.add_analyzer()
    
    # 设置初始资金
    engine.cerebro.broker.setcash(initial_capital)
    
    # 运行回测
    results = engine.run()
    
    # 分析结果
    analysis = engine.analyze_results(results)
    
    # 打印分析结果
    engine.print_analysis(analysis)
    
    # 保存结果
    engine.save_results(analysis, 'macd_backtest')
    
    # 绘制结果
    engine.plot(results, filename='macd_backtest_plot.png')


def compare_strategies():
    """
    比较不同策略的回测结果
    """
    print("\n比较不同策略的回测结果")
    
    # 设置回测参数
    stock_code = '000001'  # 平安银行
    start_date = '2020-01-01'
    end_date = '2020-12-31'
    initial_capital = 100000.0
    
    # 策略列表
    strategies = [
        {
            'name': '均线交叉策略',
            'params': {
                '短期均线': 5,
                '长期均线': 20
            }
        },
        {
            'name': 'MACD策略',
            'params': {
                'MACD快线': 12,
                'MACD慢线': 26,
                'MACD信号线': 9
            }
        }
    ]
    
    # 加载股票数据
    data = load_stock_data(stock_code, start_date, end_date)
    if data.empty:
        print(f"无法获取股票数据: {stock_code}")
        return
    
    # 存储各策略的回测结果
    results = []
    
    # 对每个策略进行回测
    for strategy in strategies:
        # 创建回测引擎
        engine = BacktestEngine()
        
        # 添加数据源
        engine.add_data(data.copy(), name=stock_code)
        
        # 准备策略参数
        strategy_params = {
            '股票代码': stock_code,
            '开始日期': start_date,
            '结束日期': end_date,
            '初始资金': initial_capital
        }
        strategy_params.update(strategy['params'])
        
        # 添加策略
        engine.add_strategy(strategy['name'], strategy_params)
        
        # 添加分析器
        engine.add_analyzer()
        
        # 设置初始资金
        engine.cerebro.broker.setcash(initial_capital)
        
        # 运行回测
        backtest_results = engine.run()
        
        # 分析结果
        analysis = engine.analyze_results(backtest_results)
        
        # 添加策略名称
        analysis['策略名称'] = strategy['name']
        
        # 存储结果
        results.append(analysis)
    
    # 比较结果
    print("\n策略比较:")
    print(f"{'策略名称':<15} {'总收益率':<10} {'年化收益率':<10} {'最大回撤':<10} {'Sharpe比率':<10} {'交易次数':<10} {'胜率':<10}")
    print("-" * 80)
    
    for result in results:
        print(f"{result['策略名称']:<15} "
              f"{result['总收益率']*100:>8.2f}% "
              f"{result['年化收益率']*100:>8.2f}% "
              f"{result['最大回撤']*100:>8.2f}% "
              f"{result['Sharpe比率']:>8.2f} "
              f"{result['交易次数']:>8} "
              f"{result['胜率']*100:>8.2f}%")
    
    # 绘制收益率比较图表
    plt.figure(figsize=(12, 6))
    
    for result in results:
        # 计算每日收益率
        daily_returns = pd.Series(result['日收益率']) if '日收益率' in result else None
        
        if daily_returns is not None and not daily_returns.empty:
            # 计算累计收益率
            cumulative_returns = (1 + daily_returns).cumprod() - 1
            
            # 绘制累计收益率曲线
            plt.plot(cumulative_returns.index, cumulative_returns.values * 100, label=result['策略名称'])
    
    plt.title('策略收益率比较')
    plt.xlabel('日期')
    plt.ylabel('累计收益率(%)')
    plt.legend()
    plt.grid(True)
    
    # 保存图表
    plt.savefig('strategy_comparison.png')
    plt.close()
    
    print("\n策略比较图表已保存到: strategy_comparison.png")


def main():
    """
    主函数
    """
    
    # 列出所有可用的策略
    strategies = strategy_factory.get_all_strategies()
    print("\n可用策略列表:")
    for i, strategy in enumerate(strategies, 1):
        print(f"{i}. {strategy}")
    
    # 运行均线交叉策略回测示例
    run_ma_cross_backtest()
    
    # 运行MACD策略回测示例
    run_macd_backtest()
    
    # 比较不同策略的回测结果
    compare_strategies()
    
    print("\n回测示例完成，可以通过以下命令运行自定义回测:")
    print("python scripts/backtest.py --strategy '均线交叉策略' --stock '000001' --start-date '2020-01-01' --end-date '2020-12-31' --capital 100000 --plot")


if __name__ == "__main__":
    main()