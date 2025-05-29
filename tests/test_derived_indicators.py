# -*- coding: utf-8 -*-

"""
衍生指标计算器测试模块

测试衍生指标计算器在各种情况下的表现，包括：
- 不同类型实体（股票、行业、指数）的指标计算
- 不同时间范围的数据处理
- 异常情况处理
- 批量处理多个实体
"""

import os
import sys
import unittest
import pandas as pd
from unittest.mock import patch, MagicMock
from pathlib import Path
import logging

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入被测试模块
from core.analyzer.derived_indicators import DerivedIndicatorCalculator

# 配置测试日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestDerivedIndicatorCalculator(unittest.TestCase):
    """测试衍生指标计算器"""

    def setUp(self):
        """测试前准备"""
        # 创建测试数据
        self.create_test_data()
        
        # 使用patch模拟TableDataReader
        self.reader_patcher = patch('core.analyzer.derived_indicators.TableDataReader')
        self.mock_reader_class = self.reader_patcher.start()
        self.mock_reader = self.mock_reader_class.return_value
        
        # 配置模拟的reader行为
        self.configure_mock_reader()
        
        # 初始化计算器
        self.calculator = DerivedIndicatorCalculator(dry_run=True)
        self.calculator.reader = self.mock_reader

    def tearDown(self):
        """测试后清理"""
        self.reader_patcher.stop()

    def create_test_data(self):
        """创建测试数据"""
        # 股票测试数据
        dates = pd.date_range(start='2023-01-01', end='2023-01-31')
        self.stock_data = pd.DataFrame({
            '日期': dates,
            '股票代码': '000001',
            '开盘价': [10 + i*0.1 for i in range(len(dates))],
            '收盘价': [10.5 + i*0.1 for i in range(len(dates))],
            '最高价': [11 + i*0.1 for i in range(len(dates))],
            '最低价': [9.5 + i*0.1 for i in range(len(dates))],
            '成交量': [1000000 + i*10000 for i in range(len(dates))],
        })
        
        # 技术指标数据
        self.tech_data = pd.DataFrame({
            '日期': dates,
            '股票代码': '000001',
            'SMA5': [10.2 + i*0.1 for i in range(len(dates))],
            'SMA20': [10.0 + i*0.05 for i in range(len(dates))],
            'RSI14': [50 + i for i in range(len(dates))],
            'MACD': [0.1 + i*0.01 for i in range(len(dates))],
        })
        
        # 行业测试数据
        self.industry_data = pd.DataFrame({
            '日期': dates,
            '行业名称': '计算机',
            '开盘价': [100 + i for i in range(len(dates))],
            '收盘价': [101 + i for i in range(len(dates))],
            '最高价': [102 + i for i in range(len(dates))],
            '最低价': [99 + i for i in range(len(dates))],
            'SMA5': [100.5 + i for i in range(len(dates))],
            'SMA20': [100 + i*0.5 for i in range(len(dates))],
        })
        
        # 指数测试数据
        self.index_data = pd.DataFrame({
            '日期': dates,
            '指数代码': '000300',
            '开盘价': [3000 + i*10 for i in range(len(dates))],
            '收盘价': [3010 + i*10 for i in range(len(dates))],
            '最高价': [3020 + i*10 for i in range(len(dates))],
            '最低价': [2990 + i*10 for i in range(len(dates))],
            'SMA5': [3005 + i*10 for i in range(len(dates))],
            'SMA20': [3000 + i*5 for i in range(len(dates))],
        })
        
        # 创建金叉信号数据
        # 在第10天和第20天创建金叉信号
        self.tech_data.loc[10, 'SMA5'] = 11.0
        self.tech_data.loc[10, 'SMA20'] = 10.9
        self.tech_data.loc[9, 'SMA5'] = 10.8
        self.tech_data.loc[9, 'SMA20'] = 10.9
        
        self.tech_data.loc[20, 'SMA5'] = 12.0
        self.tech_data.loc[20, 'SMA20'] = 11.9
        self.tech_data.loc[19, 'SMA5'] = 11.8
        self.tech_data.loc[19, 'SMA20'] = 11.9

    def configure_mock_reader(self):
        """配置模拟的数据读取器"""
        # 模拟股票历史数据读取
        self.mock_reader.read_historical_data.side_effect = lambda table_name, conditions, start_date, end_date, date_col_name: {
            "股票历史行情_后复权": self.stock_data if conditions.get("股票代码") == "000001" else pd.DataFrame(),
            "行业历史行情": self.industry_data if conditions.get("行业名称") == "计算机" else pd.DataFrame(),
            "指数历史行情": self.index_data if conditions.get("指数代码") == "000300" else pd.DataFrame(),
        }.get(table_name, pd.DataFrame())
        
        # 模拟技术指标数据读取
        self.mock_reader.read_technical_indicators.return_value = self.tech_data

    def test_stock_derived_indicator(self):
        """测试股票衍生指标计算"""
        # 处理单个股票
        self.calculator.process_entity('stock', '000001', '2023-01-01', '2023-01-31')
        
        # 验证是否调用了正确的方法
        self.mock_reader.read_historical_data.assert_called_with(
            table_name="股票历史行情_后复权",
            conditions={"股票代码": "000001"},
            start_date="2023-01-01",
            end_date="2023-01-31",
            date_col_name="日期"
        )
        self.mock_reader.read_technical_indicators.assert_called_with(
            stock_code="000001",
            start_date="2023-01-01",
            end_date="2023-01-31"
        )

    def test_industry_derived_indicator(self):
        """测试行业衍生指标计算"""
        # 处理单个行业
        self.calculator.process_entity('industry', '计算机', '2023-01-01', '2023-01-31')
        
        # 验证是否调用了正确的方法
        self.mock_reader.read_historical_data.assert_called_with(
            table_name="行业历史行情",
            conditions={"行业名称": "计算机"},
            start_date="2023-01-01",
            end_date="2023-01-31",
            date_col_name="日期"
        )

    def test_index_derived_indicator(self):
        """测试指数衍生指标计算"""
        # 处理单个指数
        self.calculator.process_entity('index', '000300', '2023-01-01', '2023-01-31')
        
        # 验证是否调用了正确的方法
        self.mock_reader.read_historical_data.assert_called_with(
            table_name="指数历史行情",
            conditions={"指数代码": "000300"},
            start_date="2023-01-01",
            end_date="2023-01-31",
            date_col_name="日期"
        )

    def test_golden_cross_calculation(self):
        """测试金叉信号计算"""
        # 创建测试数据
        test_df = pd.DataFrame({
            '日期': pd.date_range(start='2023-01-01', periods=5),
            'SMA5': [9, 10, 11, 12, 13],
            'SMA20': [10, 10, 10, 10, 10]
        })
        
        # 计算金叉信号
        result_df = self.calculator.calculate_example_derived_indicator(test_df)
        
        # 验证结果
        self.assertIn('golden_cross', result_df.columns)
        # 第二天应该有金叉信号 (SMA5从9变为10，超过SMA20)
        self.assertEqual(result_df.iloc[1]['golden_cross'], 1)
        # 其他天应该没有金叉信号
        self.assertEqual(result_df.iloc[0]['golden_cross'], 0)  # 第一天无法计算（需要前一天数据）
        self.assertEqual(result_df.iloc[2]['golden_cross'], 0)  # 已经是金叉状态
        self.assertEqual(result_df.iloc[3]['golden_cross'], 0)  # 已经是金叉状态
        self.assertEqual(result_df.iloc[4]['golden_cross'], 0)  # 已经是金叉状态

    def test_missing_data_handling(self):
        """测试缺失数据处理"""
        # 测试缺少SMA5列的情况
        test_df = pd.DataFrame({
            '日期': pd.date_range(start='2023-01-01', periods=5),
            'SMA20': [10, 10, 10, 10, 10]
        })
        
        # 计算金叉信号
        result_df = self.calculator.calculate_example_derived_indicator(test_df)
        
        # 验证结果 - 应该返回原始DataFrame，没有添加golden_cross列
        self.assertNotIn('golden_cross', result_df.columns)
        
        # 测试空DataFrame
        empty_df = pd.DataFrame()
        result_df = self.calculator.calculate_example_derived_indicator(empty_df)
        self.assertTrue(result_df.empty)

    def test_batch_processing(self):
        """测试批量处理多个实体"""
        # 设置要处理的实体
        specific_entities = {
            'stock': ['000001'],
            'industry': ['计算机'],
            'index': ['000300']
        }
        
        # 运行批量处理
        self.calculator.run(data_types=['stock', 'industry', 'index'], specific_entities=specific_entities)
        
        # 验证是否处理了所有实体
        # 由于process_entity在run中被调用了3次，我们可以检查read_historical_data的调用次数
        self.assertEqual(self.mock_reader.read_historical_data.call_count, 3)

    def test_date_range_filtering(self):
        """测试日期范围过滤"""
        # 使用不同的日期范围
        self.calculator.process_entity('stock', '000001', '2023-01-10', '2023-01-20')
        
        # 验证是否使用了正确的日期范围
        self.mock_reader.read_historical_data.assert_called_with(
            table_name="股票历史行情_后复权",
            conditions={"股票代码": "000001"},
            start_date="2023-01-10",
            end_date="2023-01-20",
            date_col_name="日期"
        )

    def test_nonexistent_entity(self):
        """测试不存在的实体"""
        # 处理不存在的股票
        self.calculator.process_entity('stock', '999999', '2023-01-01', '2023-01-31')
        
        # 验证是否调用了正确的方法，但应该没有数据返回
        self.mock_reader.read_historical_data.assert_called_with(
            table_name="股票历史行情_后复权",
            conditions={"股票代码": "999999"},
            start_date="2023-01-01",
            end_date="2023-01-31",
            date_col_name="日期"
        )
        # 由于模拟的reader对于999999返回空DataFrame，所以不应该有进一步的处理


if __name__ == "__main__":
    unittest.main()