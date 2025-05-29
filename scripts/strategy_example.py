# -*- coding: utf-8 -*-
"""
策略模块使用示例脚本

展示如何使用策略模块进行回测，以及如何扩展新的策略
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import logging

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入策略模块
from core.strategy.strategy_factory import strategy_factory


def setup_logging():
    """
    设置日志
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def list_available_strategies():
    """
    列出所有可用的策略
    """
    strategies = strategy_factory.get_all_strategies()
    print("\n可用策略列表:")
    for i, strategy in enumerate(strategies, 1):
        print(f"{i}. {strategy}")
    return strategies


def get_strategy_params(strategy_name):
    """
    获取策略参数模式并提示用户输入
    
    Args:
        strategy_name: 策略名称
        
    Returns:
        策略参数字典
    """
    # 获取参数模式
    param_schema = strategy_factory.get_strategy_param_schema(strategy_name)
    
    # 使用默认参数
    params = {}
    for param_name, param_info in param_schema.items():
        params[param_name] = param_info.get('default')
    
    # 设置示例股票和日期
    params['股票代码'] = '000001'  # 平安银行
    params['开始日期'] = '2020-01-01'
    params['结束日期'] = '2020-12-31'
    
    return params


def run_strategy_backtest(strategy_name, params):
    """
    运行策略回测
    
    Args:
        strategy_name: 策略名称
        params: 策略参数
        
    Returns:
        回测结果
    """
    # 创建策略实例
    strategy = strategy_factory.create_strategy(strategy_name, params)
    
    # 运行回测
    result = strategy.run_backtest()
    
    return result


def display_backtest_result(result):
    """
    显示回测结果
    
    Args:
        result: 回测结果字典
    """
    print("\n回测结果:")
    print(f"策略名称: {result['策略名称']}")
    print(f"回测区间: {result['开始日期']} 至 {result['结束日期']}")
    print(f"初始资金: {result['初始资金']:.2f}")
    print(f"最终资金: {result['最终资金']:.2f}")
    print(f"总收益率: {result['总收益率']*100:.2f}%")
    print(f"年化收益率: {result['年化收益率']*100:.2f}%")
    print(f"最大回撤: {result['最大回撤']*100:.2f}%")
    print(f"Sharpe比率: {result['Sharpe比率']:.2f}")
    print(f"交易次数: {result['交易次数']}")
    print(f"胜率: {result['胜率']*100:.2f}%")
    
    # 显示交易记录
    if result['交易记录']:
        print("\n交易记录:")
        for i, trade in enumerate(result['交易记录'][:5], 1):  # 只显示前5条
            print(f"{i}. 日期: {trade['日期']}, 操作: {trade['操作']}, "
                  f"价格: {trade['价格']:.2f}, 数量: {trade['数量']}")
        if len(result['交易记录']) > 5:
            print(f"... 共{len(result['交易记录'])}条交易记录")


def save_strategy_example():
    """
    保存策略配置示例
    """
    # 创建均线交叉策略
    params = {
        '股票代码': '000001',
        '开始日期': '2020-01-01',
        '结束日期': '2020-12-31',
        '初始资金': 100000.0,
        '短期均线': 5,
        '长期均线': 20
    }
    strategy = strategy_factory.create_strategy('均线交叉策略', params)
    
    # 保存策略配置
    file_path = strategy_factory.save_strategy_config(strategy, 'ma_cross_example.json')
    print(f"\n策略配置已保存到: {file_path}")
    
    # 加载策略配置
    loaded_strategy = strategy_factory.load_strategy_config(file_path)
    print(f"已加载策略: {loaded_strategy.name}, ID: {loaded_strategy.strategy_id}")


def create_custom_strategy_example():
    """
    创建自定义策略示例
    
    展示如何创建新的策略类并集成到系统中
    """
    print("\n创建自定义策略示例:")

# 自定义策略示例代码:

from core.strategy.strategy_base import StrategyBase
import pandas as pd

@StrategyBase.register_strategy("双均线策略")
class DoubleMACrossStrategy(StrategyBase):
    """双均线交叉策略"""    
    def _init_strategy_params(self):
        self.short_period = self.params.get('短期均线', 5)
        self.middle_period = self.params.get('中期均线', 10)
        self.long_period = self.params.get('长期均线', 20)
    
    def generate_signals(self, data):
        df = data.copy()
        
        if '收盘价' in df.columns:
            df['短期均线'] = df['收盘价'].rolling(window=self.short_period).mean()
            df['中期均线'] = df['收盘价'].rolling(window=self.middle_period).mean()
            df['长期均线'] = df['收盘价'].rolling(window=self.long_period).mean()
            
            df['信号'] = 0
            
            # 短期均线上穿中期均线且中期均线上穿长期均线，买入信号
            df.loc[(df['短期均线'] > df['中期均线']) & 
                   (df['中期均线'] > df['长期均线']) & 
                   ((df['短期均线'].shift(1) <= df['中期均线'].shift(1)) | 
                    (df['中期均线'].shift(1) <= df['长期均线'].shift(1))), '信号'] = 1
            
            # 短期均线下穿中期均线或中期均线下穿长期均线，卖出信号
            df.loc[(df['短期均线'] < df['中期均线']) | 
                   (df['中期均线'] < df['长期均线']), '信号'] = -1
        
        return df
    
    def get_param_schema(self):
        schema = super().get_param_schema()
        
        schema.update({
            '短期均线': {
                'type': 'integer',
                'default': 5,
                'min': 1,
                'max': 60,
                'description': '短期均线周期'
            },
            '中期均线': {
                'type': 'integer',
                'default': 10,
                'min': 5,
                'max': 120,
                'description': '中期均线周期'
            },
            '长期均线': {
                'type': 'integer',
                'default': 20,
                'min': 10,
                'max': 250,
                'description': '长期均线周期'
            }
        })
        
        return schema
    


def main():
    """
    主函数
    """
    setup_logging()
    
    print("策略模块使用示例")
    print("=" * 50)
    
    # 列出可用策略
    strategies = list_available_strategies()
    
    # 选择策略进行回测
    strategy_name = strategies[0]  # 默认使用第一个策略
    print(f"\n选择策略: {strategy_name}")
    
    # 获取策略参数
    params = get_strategy_params(strategy_name)
    print("\n策略参数:")
    for key, value in params.items():
        print(f"{key}: {value}")
    
    # 运行回测
    print("\n运行回测...")
    result = run_strategy_backtest(strategy_name, params)
    
    # 显示回测结果
    display_backtest_result(result)
    
    # 保存策略示例
    save_strategy_example()
    
    # 创建自定义策略示例
    create_custom_strategy_example()
    
    print("\n示例完成!")


if __name__ == "__main__":
    main()