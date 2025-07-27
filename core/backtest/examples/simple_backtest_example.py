# -*- coding: utf-8 -*-
"""
简单回测示例

演示如何使用回测模块进行基本的策略回测
"""

import os
import sys
from datetime import datetime, date

# 添加项目根目录到系统路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from core.backtest import (
    create_backtest_engine, 
    create_portfolio_manager,
    create_performance_analyzer,
    create_visualizer
)
from core.strategy.strategy_manager import StrategyManager
from utils.logger import LoggerManager


def simple_backtest_example():
    """
    简单回测示例
    """
    # 获取日志记录器
    logger_manager = LoggerManager()
    logger = logger_manager.get_logger('simple_backtest')
    
    logger.info("开始简单回测示例")
    
    try:
        # 1. 配置回测参数
        config = {
            'initial_capital': 1000000,  # 初始资金100万
            'commission': 0.0003,        # 手续费0.03%
            'slippage': 0.001,          # 滑点0.1%
            'risk_free_rate': 0.03,     # 无风险利率3%
            'max_position_size': 0.1,   # 单股最大仓位10%
            'max_positions': 10         # 最大持仓数量
        }
        
        logger.info(f"回测配置: {config}")
        
        # 2. 创建回测引擎
        engine = create_backtest_engine(config)
        logger.info("回测引擎创建成功")
        
        # 3. 加载策略
        strategy_manager = StrategyManager()
        available_strategies = strategy_manager.list_strategies()
        logger.info(f"可用策略: {available_strategies}")
        
        # 选择第一个可用策略（如果有的话）
        if available_strategies:
            strategy_name = available_strategies[0]
            strategy = strategy_manager.get_strategy(strategy_name)
            logger.info(f"已加载策略: {strategy_name}")
        else:
            logger.warning("没有可用策略，使用默认策略")
            # 这里可以创建一个简单的默认策略
            strategy = None
        
        # 4. 设置回测参数
        backtest_params = {
            'start_date': '2023-01-01',
            'end_date': '2023-12-31',
            'stock_codes': ['000001.SZ', '000002.SZ', '000858.SZ'],  # 示例股票
            'benchmark': '000300.SH'  # 沪深300作为基准
        }
        
        logger.info(f"回测参数: {backtest_params}")
        
        # 5. 运行回测
        logger.info("开始运行回测...")
        
        if strategy:
            results = engine.run_backtest(
                strategy=strategy,
                **backtest_params
            )
            
            logger.info("回测完成")
            
            # 6. 分析结果
            if results and 'portfolio_values' in results:
                logger.info("开始分析回测结果...")
                
                # 创建绩效分析器
                analyzer = create_performance_analyzer(config)
                
                # 计算绩效指标
                metrics = analyzer.calculate_metrics(
                    portfolio_values=results['portfolio_values'],
                    trades=results.get('trades', []),
                    benchmark_values=results.get('benchmark_values')
                )
                
                # 打印关键指标
                logger.info("=== 回测结果 ===")
                logger.info(f"总收益率: {metrics.total_return:.2%}")
                logger.info(f"年化收益率: {metrics.annual_return:.2%}")
                logger.info(f"最大回撤: {metrics.max_drawdown:.2%}")
                logger.info(f"夏普比率: {metrics.sharpe_ratio:.4f}")
                logger.info(f"胜率: {metrics.win_rate:.2%}")
                logger.info(f"盈亏比: {metrics.profit_factor:.2f}")
                logger.info(f"总交易次数: {metrics.total_trades}")
                
                # 7. 生成可视化报告
                logger.info("生成可视化报告...")
                
                visualizer = create_visualizer('simple_backtest_results')
                
                # 生成综合报告
                report_path = visualizer.create_comprehensive_report(
                    portfolio_values=results['portfolio_values'],
                    trades=results.get('trades', []),
                    metrics=metrics,
                    benchmark_values=results.get('benchmark_values')
                )
                
                if report_path:
                    logger.info(f"回测报告已生成: {report_path}")
                    print(f"\n📊 回测报告已生成: {report_path}")
                    print("请在浏览器中打开查看详细结果")
                else:
                    logger.warning("报告生成失败")
                
                # 8. 保存结果
                from core.backtest.utils import FileUtils
                
                save_success = FileUtils.save_results(
                    {
                        'config': config,
                        'backtest_params': backtest_params,
                        'metrics': metrics.to_dict(),
                        'portfolio_values': results['portfolio_values'],
                        'trades': [trade.__dict__ for trade in results.get('trades', [])]
                    },
                    'simple_backtest_results/backtest_results.json'
                )
                
                if save_success:
                    logger.info("回测结果已保存")
                else:
                    logger.warning("结果保存失败")
                
            else:
                logger.error("回测结果为空或格式错误")
                
        else:
            logger.error("无法运行回测：没有可用策略")
            print("\n❌ 无法运行回测：没有可用策略")
            print("请先在 core/strategy 目录下创建策略文件")
            
    except Exception as e:
        logger.error(f"回测过程中发生错误: {e}")
        print(f"\n❌ 回测失败: {e}")
        import traceback
        traceback.print_exc()


def advanced_backtest_example():
    """
    高级回测示例 - 展示更多配置选项
    """
    from core.backtest import (
        BacktestEngine, PortfolioManager, OrderExecutor,
        FixedCommissionModel, VolumeBasedSlippageModel,
        DataProcessor
    )
    
    # 获取日志记录器
    logger_manager = LoggerManager()
    logger = logger_manager.get_logger('advanced_backtest')
    
    logger.info("开始高级回测示例")
    
    try:
        # 1. 创建自定义组件
        
        # 投资组合管理器
        portfolio_manager = PortfolioManager(
            initial_capital=5000000,  # 500万初始资金
            max_position_size=0.05,   # 单股最大仓位5%
            max_positions=20          # 最大持仓20只
        )
        
        # 订单执行器
        order_executor = OrderExecutor(
            commission_model=FixedCommissionModel(0.0003),
            slippage_model=VolumeBasedSlippageModel(base_slippage=0.001, volume_factor=0.1)
        )
        
        # 数据处理器
        data_processor = DataProcessor(cache_enabled=True)
        
        # 2. 创建回测引擎
        engine = BacktestEngine(
            portfolio_manager=portfolio_manager,
            order_executor=order_executor,
            data_processor=data_processor
        )
        
        logger.info("高级回测引擎创建成功")
        
        # 3. 预加载数据
        stock_codes = ['000001.SZ', '000002.SZ', '000858.SZ', '600000.SH', '600036.SH']
        
        data_processor.preload_data(
            stock_codes=stock_codes,
            start_date='2022-01-01',
            end_date='2023-12-31'
        )
        
        logger.info("数据预加载完成")
        
        # 4. 运行回测（这里需要实际的策略）
        logger.info("高级回测配置完成，等待策略实现")
        print("\n✅ 高级回测配置完成")
        print("配置详情:")
        print(f"  - 初始资金: {portfolio_manager.initial_capital:,}")
        print(f"  - 最大持仓: {portfolio_manager.max_positions}")
        print(f"  - 单股最大仓位: {portfolio_manager.max_position_size:.1%}")
        print(f"  - 股票池: {len(stock_codes)} 只股票")
        
    except Exception as e:
        logger.error(f"高级回测配置失败: {e}")
        print(f"\n❌ 高级回测配置失败: {e}")


def performance_analysis_example():
    """
    绩效分析示例
    """
    from core.backtest import PerformanceAnalyzer, PerformanceMetrics
    import pandas as pd
    import numpy as np
    
    # 获取日志记录器
    logger_manager = LoggerManager()
    logger = logger_manager.get_logger('performance_analysis')
    
    logger.info("开始绩效分析示例")
    
    try:
        # 1. 创建模拟数据
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
        
        # 模拟投资组合价值（随机游走）
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.02, len(dates))  # 日收益率
        portfolio_values = []
        current_value = 1000000  # 初始100万
        
        for i, date in enumerate(dates):
            current_value *= (1 + returns[i])
            portfolio_values.append({
                '日期': date.strftime('%Y-%m-%d'),
                '总价值': current_value,
                '现金': current_value * 0.1,
                '持仓价值': current_value * 0.9
            })
        
        logger.info(f"生成了 {len(portfolio_values)} 天的模拟数据")
        
        # 2. 创建绩效分析器
        analyzer = PerformanceAnalyzer(risk_free_rate=0.03)
        
        # 3. 计算绩效指标
        metrics = analyzer.calculate_metrics(
            portfolio_values=portfolio_values,
            trades=[],  # 空交易列表
            benchmark_values=None
        )
        
        # 4. 显示结果
        logger.info("=== 绩效分析结果 ===")
        print("\n📈 绩效分析结果:")
        print(f"总收益率: {metrics.total_return:.2%}")
        print(f"年化收益率: {metrics.annual_return:.2%}")
        print(f"年化波动率: {metrics.volatility:.2%}")
        print(f"最大回撤: {metrics.max_drawdown:.2%}")
        print(f"夏普比率: {metrics.sharpe_ratio:.4f}")
        print(f"索提诺比率: {metrics.sortino_ratio:.4f}")
        print(f"卡玛比率: {metrics.calmar_ratio:.4f}")
        print(f"VaR (95%): {metrics.var_95:.2%}")
        print(f"CVaR (95%): {metrics.cvar_95:.2%}")
        
        # 5. 生成可视化
        visualizer = create_visualizer('performance_analysis_results')
        
        # 生成单个图表
        visualizer.plot_portfolio_value(portfolio_values)
        visualizer.plot_returns(portfolio_values)
        visualizer.plot_drawdown(portfolio_values)
        visualizer.plot_risk_metrics(metrics)
        
        logger.info("绩效分析图表已生成")
        print("\n📊 分析图表已生成到 performance_analysis_results 目录")
        
    except Exception as e:
        logger.error(f"绩效分析失败: {e}")
        print(f"\n❌ 绩效分析失败: {e}")


if __name__ == '__main__':
    print("🚀 回测模块示例")
    print("=" * 50)
    
    # 选择要运行的示例
    examples = {
        '1': ('简单回测示例', simple_backtest_example),
        '2': ('高级回测示例', advanced_backtest_example),
        '3': ('绩效分析示例', performance_analysis_example)
    }
    
    print("\n请选择要运行的示例:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    
    choice = input("\n请输入选择 (1-3, 或按回车运行所有示例): ").strip()
    
    if choice in examples:
        name, func = examples[choice]
        print(f"\n运行 {name}...")
        func()
    else:
        # 运行所有示例
        print("\n运行所有示例...")
        for name, func in examples.values():
            print(f"\n{'='*20} {name} {'='*20}")
            func()
    
    print("\n✅ 示例运行完成")