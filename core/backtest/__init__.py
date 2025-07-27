# -*- coding: utf-8 -*-
"""
回测模块

提供通用的股票策略回测功能，支持多种策略类型和数据源
"""

# 版本信息
__version__ = '1.0.0'
__author__ = 'Stock Analysis Team'
__description__ = '通用股票策略回测框架'

# 导入核心类
from .backtest_engine import BacktestEngine, AKShareDataFeed, StrategyAdapter
from .data_processor import DataProcessor
from .portfolio_manager import (
    PortfolioManager, Position, Trade, 
    RiskManager, PositionSizer
)
from .order_executor import (
    OrderExecutor, AdvancedOrderExecutor,
    ExecutionModel, SlippageModel, CommissionModel,
    FixedSlippageModel, VolumeBasedSlippageModel, BidAskSlippageModel,
    FixedCommissionModel, TieredCommissionModel,
    MarketImpactModel
)
from .performance_analyzer import PerformanceAnalyzer, PerformanceMetrics
from .visualizer import BacktestVisualizer
from .utils import (
    DateUtils, DataUtils, RiskUtils, PerformanceUtils,
    ValidationUtils, FileUtils, LogUtils
)

# 导出的公共接口
__all__ = [
    # 核心引擎
    'BacktestEngine',
    'AKShareDataFeed',
    'StrategyAdapter',
    
    # 数据处理
    'DataProcessor',
    
    # 投资组合管理
    'PortfolioManager',
    'Position',
    'Trade',
    'RiskManager',
    'PositionSizer',
    
    # 订单执行
    'OrderExecutor',
    'AdvancedOrderExecutor',
    'ExecutionModel',
    'SlippageModel',
    'CommissionModel',
    'FixedSlippageModel',
    'VolumeBasedSlippageModel',
    'BidAskSlippageModel',
    'FixedCommissionModel',
    'TieredCommissionModel',
    'MarketImpactModel',
    
    # 绩效分析
    'PerformanceAnalyzer',
    'PerformanceMetrics',
    
    # 可视化
    'BacktestVisualizer',
    
    # 工具函数
    'DateUtils',
    'DataUtils',
    'RiskUtils',
    'PerformanceUtils',
    'ValidationUtils',
    'FileUtils',
    'LogUtils',
]

# 模块级别的配置
DEFAULT_CONFIG = {
    'initial_capital': 1000000,  # 默认初始资金100万
    'commission': 0.0003,        # 默认手续费0.03%
    'slippage': 0.001,          # 默认滑点0.1%
    'risk_free_rate': 0.03,     # 默认无风险利率3%
    'benchmark': '000300.SH',   # 默认基准指数（沪深300）
    'max_position_size': 0.1,   # 默认单个股票最大仓位10%
    'max_positions': 10,        # 默认最大持仓数量
}


def get_default_config():
    """
    获取默认配置
    
    Returns:
        dict: 默认配置字典
    """
    return DEFAULT_CONFIG.copy()


def create_backtest_engine(config=None):
    """
    创建回测引擎的便捷函数
    
    Args:
        config (dict, optional): 配置参数
        
    Returns:
        BacktestEngine: 回测引擎实例
    """
    if config is None:
        config = get_default_config()
    
    return BacktestEngine(
        initial_cash=config.get('initial_capital', DEFAULT_CONFIG['initial_capital'])
    )


def create_portfolio_manager(config=None):
    """
    创建投资组合管理器的便捷函数
    
    Args:
        config (dict, optional): 配置参数
        
    Returns:
        PortfolioManager: 投资组合管理器实例
    """
    if config is None:
        config = get_default_config()
    
    return PortfolioManager(
        initial_capital=config.get('initial_capital', DEFAULT_CONFIG['initial_capital']),
        max_position_size=config.get('max_position_size', DEFAULT_CONFIG['max_position_size']),
        max_positions=config.get('max_positions', DEFAULT_CONFIG['max_positions'])
    )


def create_performance_analyzer(config=None):
    """
    创建绩效分析器的便捷函数
    
    Args:
        config (dict, optional): 配置参数
        
    Returns:
        PerformanceAnalyzer: 绩效分析器实例
    """
    if config is None:
        config = get_default_config()
    
    return PerformanceAnalyzer(
        risk_free_rate=config.get('risk_free_rate', DEFAULT_CONFIG['risk_free_rate'])
    )


def create_visualizer(output_dir='backtest_results'):
    """
    创建可视化器的便捷函数
    
    Args:
        output_dir (str): 输出目录
        
    Returns:
        BacktestVisualizer: 可视化器实例
    """
    return BacktestVisualizer(output_dir=output_dir)


# 模块信息
def get_module_info():
    """
    获取模块信息
    
    Returns:
        dict: 模块信息
    """
    return {
        'name': 'backtest',
        'version': __version__,
        'author': __author__,
        'description': __description__,
        'components': [
            'BacktestEngine - 回测引擎',
            'DataProcessor - 数据处理器',
            'PortfolioManager - 投资组合管理器',
            'OrderExecutor - 订单执行器',
            'PerformanceAnalyzer - 绩效分析器',
            'BacktestVisualizer - 结果可视化器',
            'Utils - 工具函数集合'
        ]
    }


# 快速开始示例
def quick_start_example():
    """
    快速开始示例代码
    
    Returns:
        str: 示例代码
    """
    example_code = '''
# 快速开始示例
from core.backtest import create_backtest_engine, create_visualizer
from core.strategy.strategy_manager import StrategyManager

# 1. 创建回测引擎
engine = create_backtest_engine({
    'initial_capital': 1000000,
    'commission': 0.0003,
    'slippage': 0.001
})

# 2. 加载策略
strategy_manager = StrategyManager()
strategy = strategy_manager.get_strategy('your_strategy_name')

# 3. 运行回测
results = engine.run_backtest(
    strategy=strategy,
    start_date='2023-01-01',
    end_date='2023-12-31',
    stock_codes=['000001.SZ', '000002.SZ']
)

# 4. 生成报告
visualizer = create_visualizer()
report_path = visualizer.create_comprehensive_report(
    portfolio_values=results['portfolio_values'],
    trades=results['trades'],
    metrics=results['metrics']
)

print(f"回测报告已生成: {report_path}")
'''
    return example_code


if __name__ == '__main__':
    # 打印模块信息
    info = get_module_info()
    print(f"模块: {info['name']}")
    print(f"版本: {info['version']}")
    print(f"作者: {info['author']}")
    print(f"描述: {info['description']}")
    print("\n组件:")
    for component in info['components']:
        print(f"  - {component}")
    
    print("\n快速开始示例:")
    print(quick_start_example())