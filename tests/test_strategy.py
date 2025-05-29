# -*- coding: utf-8 -*-
"""
策略模块单元测试

测试策略模式的可扩展性设计是否正常工作
"""

import os
import sys
import unittest
import pandas as pd
import numpy as np
import datetime
import tempfile
import json

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入策略模块
from core.strategy.strategy_base import StrategyBase
from core.strategy.strategy_factory import strategy_factory
from core.strategy.momentum_strategy import MACrossStrategy, MACDStrategy, KDJStrategy
from core.strategy.value_strategy import LowValuationStrategy, QualityGrowthStrategy, DividendStrategy


class TestStrategyBase(unittest.TestCase):
    """测试策略基类"""
    
    def test_strategy_registry(self):
        """测试策略注册机制"""
        # 检查策略注册表是否包含预期的策略
        strategies = StrategyBase.list_strategies()
        self.assertIn('均线交叉策略', strategies)
        self.assertIn('MACD策略', strategies)
        self.assertIn('KDJ策略', strategies)
        self.assertIn('低估值策略', strategies)
        self.assertIn('质量成长策略', strategies)
        self.assertIn('股息策略', strategies)
    
    def test_get_strategy_class(self):
        """测试获取策略类"""
        # 获取已注册的策略类
        strategy_class = StrategyBase.get_strategy_class('均线交叉策略')
        self.assertEqual(strategy_class, MACrossStrategy)
        
        # 测试获取不存在的策略类
        with self.assertRaises(KeyError):
            StrategyBase.get_strategy_class('不存在的策略')
    
    def test_param_schema(self):
        """测试参数模式定义"""
        # 创建策略实例
        strategy = MACrossStrategy('测试策略', {'短期均线': 5, '长期均线': 20})
        
        # 获取参数模式
        schema = strategy.get_param_schema()
        
        # 检查基础参数
        self.assertIn('股票代码', schema)
        self.assertIn('开始日期', schema)
        self.assertIn('结束日期', schema)
        self.assertIn('初始资金', schema)
        
        # 检查策略特定参数
        self.assertIn('短期均线', schema)
        self.assertIn('长期均线', schema)
        
        # 检查参数属性
        self.assertEqual(schema['短期均线']['type'], 'integer')
        self.assertEqual(schema['短期均线']['default'], 5)
        self.assertEqual(schema['短期均线']['min'], 1)
        self.assertEqual(schema['短期均线']['max'], 120)
    
    def test_strategy_save_load(self):
        """测试策略配置的保存和加载"""
        # 创建策略实例
        params = {
            '股票代码': '000001',
            '开始日期': '2020-01-01',
            '结束日期': '2020-12-31',
            '初始资金': 100000.0,
            '短期均线': 5,
            '长期均线': 20
        }
        strategy = MACrossStrategy('测试策略', params)
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp:
            temp_path = temp.name
        
        try:
            # 保存策略配置
            saved_path = strategy.save_strategy(temp_path)
            self.assertEqual(saved_path, temp_path)
            
            # 检查文件是否存在
            self.assertTrue(os.path.exists(temp_path))
            
            # 检查文件内容
            with open(temp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.assertEqual(data['name'], '测试策略')
                self.assertEqual(data['strategy_class'], 'MACrossStrategy')
                self.assertEqual(data['params']['短期均线'], 5)
                self.assertEqual(data['params']['长期均线'], 20)
            
            # 加载策略配置
            loaded_strategy = StrategyBase.load_strategy(temp_path)
            self.assertIsInstance(loaded_strategy, MACrossStrategy)
            self.assertEqual(loaded_strategy.name, '测试策略')
            self.assertEqual(loaded_strategy.params['短期均线'], 5)
            self.assertEqual(loaded_strategy.params['长期均线'], 20)
        finally:
            # 删除临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestStrategyFactory(unittest.TestCase):
    """测试策略工厂"""
    
    def test_get_all_strategies(self):
        """测试获取所有策略"""
        strategies = strategy_factory.get_all_strategies()
        self.assertIsInstance(strategies, list)
        self.assertGreater(len(strategies), 0)
        self.assertIn('均线交叉策略', strategies)
    
    def test_get_strategy_param_schema(self):
        """测试获取策略参数模式"""
        schema = strategy_factory.get_strategy_param_schema('MACD策略')
        self.assertIsInstance(schema, dict)
        self.assertIn('快线周期', schema)
        self.assertIn('慢线周期', schema)
        self.assertIn('信号周期', schema)
    
    def test_create_strategy(self):
        """测试创建策略实例"""
        params = {
            '股票代码': '000001',
            '开始日期': '2020-01-01',
            '结束日期': '2020-12-31',
            '初始资金': 100000.0,
            'K周期': 9,
            'D周期': 3
        }
        strategy = strategy_factory.create_strategy('KDJ策略', params)
        self.assertIsInstance(strategy, KDJStrategy)
        self.assertEqual(strategy.params['K周期'], 9)
        self.assertEqual(strategy.params['D周期'], 3)


class TestMomentumStrategy(unittest.TestCase):
    """测试动量策略"""
    
    def setUp(self):
        """准备测试数据"""
        # 创建测试数据
        dates = pd.date_range(start='2020-01-01', periods=100, freq='D')
        prices = np.random.normal(100, 10, 100).cumsum() + 1000
        self.test_data = pd.DataFrame({
            '收盘价': prices,
            '开盘价': prices * 0.99,
            '最高价': prices * 1.01,
            '最低价': prices * 0.98,
            '成交量': np.random.randint(1000, 10000, 100)
        }, index=dates)
    
    def test_ma_cross_strategy(self):
        """测试均线交叉策略"""
        # 创建策略实例
        params = {
            '短期均线': 5,
            '长期均线': 20
        }
        strategy = MACrossStrategy('均线测试', params)
        
        # 生成信号
        signals = strategy.generate_signals(self.test_data)
        
        # 检查信号列是否存在
        self.assertIn('信号', signals.columns)
        
        # 检查是否有买入和卖出信号
        self.assertTrue((signals['信号'] == 1).any() or (signals['信号'] == -1).any())
    
    def test_macd_strategy(self):
        """测试MACD策略"""
        # 创建策略实例
        params = {
            '快线周期': 12,
            '慢线周期': 26,
            '信号周期': 9
        }
        strategy = MACDStrategy('MACD测试', params)
        
        # 生成信号
        signals = strategy.generate_signals(self.test_data)
        
        # 检查信号列是否存在
        self.assertIn('信号', signals.columns)


class TestValueStrategy(unittest.TestCase):
    """测试价值策略"""
    
    def setUp(self):
        """准备测试数据"""
        # 创建测试数据
        dates = pd.date_range(start='2020-01-01', periods=100, freq='D')
        prices = np.random.normal(100, 10, 100).cumsum() + 1000
        pe_values = np.random.normal(15, 5, 100)
        pb_values = np.random.normal(1.5, 0.5, 100)
        roe_values = np.random.normal(15, 3, 100)
        
        self.test_data = pd.DataFrame({
            '收盘价': prices,
            'PE': pe_values,
            'PB': pb_values,
            'ROE': roe_values,
            '净利润增长率': np.random.normal(20, 10, 100),
            '营收增长率': np.random.normal(15, 8, 100),
            '股息率': np.random.normal(3, 1, 100),
            '连续分红年数': np.random.randint(0, 10, 100)
        }, index=dates)
    
    def test_low_valuation_strategy(self):
        """测试低估值策略"""
        # 创建策略实例
        params = {
            'PE阈值': 15,
            'PB阈值': 1.5,
            '使用PE': True,
            '使用PB': True
        }
        strategy = LowValuationStrategy('低估值测试', params)
        
        # 生成信号
        signals = strategy.generate_signals(self.test_data)
        
        # 检查信号列是否存在
        self.assertIn('信号', signals.columns)
    
    def test_quality_growth_strategy(self):
        """测试质量成长策略"""
        # 创建策略实例
        params = {
            'ROE阈值': 15,
            '净利润增长率阈值': 20,
            '营收增长率阈值': 15,
            '使用ROE': True,
            '使用净利润增长率': True,
            '使用营收增长率': True
        }
        strategy = QualityGrowthStrategy('质量成长测试', params)
        
        # 生成信号
        signals = strategy.generate_signals(self.test_data)
        
        # 检查信号列是否存在
        self.assertIn('信号', signals.columns)
        self.assertIn('信号分数', signals.columns)


class TestStrategyExtensibility(unittest.TestCase):
    """测试策略可扩展性"""
    
    def test_custom_strategy(self):
        """测试自定义策略"""
        # 定义一个新的策略类
        @StrategyBase.register_strategy("测试策略")
        class TestStrategy(StrategyBase):
            def _init_strategy_params(self):
                self.threshold = self.params.get('阈值', 50)
            
            def generate_signals(self, data):
                df = data.copy()
                df['信号'] = 0
                if '收盘价' in df.columns:
                    df.loc[df['收盘价'] > self.threshold, '信号'] = 1
                    df.loc[df['收盘价'] < self.threshold, '信号'] = -1
                return df
            
            def get_param_schema(self):
                schema = super().get_param_schema()
                schema.update({
                    '阈值': {
                        'type': 'number',
                        'default': 50,
                        'min': 0,
                        'max': 100,
                        'description': '价格阈值'
                    }
                })
                return schema
        
        # 检查策略是否已注册
        self.assertIn('测试策略', StrategyBase.list_strategies())
        
        # 创建策略实例
        params = {'阈值': 50}
        strategy = strategy_factory.create_strategy('测试策略', params)
        
        # 检查策略类型
        self.assertIsInstance(strategy, TestStrategy)
        
        # 检查参数
        self.assertEqual(strategy.params['阈值'], 50)
        
        # 生成信号
        dates = pd.date_range(start='2020-01-01', periods=10, freq='D')
        prices = [40, 45, 55, 60, 50, 45, 40, 60, 65, 55]
        test_data = pd.DataFrame({'收盘价': prices}, index=dates)
        
        signals = strategy.generate_signals(test_data)
        
        # 检查信号
        self.assertEqual(signals.loc[dates[0], '信号'], -1)  # 40 < 50, 卖出
        self.assertEqual(signals.loc[dates[2], '信号'], 1)   # 55 > 50, 买入


if __name__ == '__main__':
    unittest.main()