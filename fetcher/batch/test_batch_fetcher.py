#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
批量股票历史数据获取工具测试脚本

用于测试和验证批量获取功能是否正常工作
包含单元测试和集成测试
"""

import os
import sys
import time
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd
import datetime

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from fetcher.batch.batch_historical_fetcher import BatchHistoricalFetcher
    from fetcher.batch.enhanced_batch_fetcher import EnhancedBatchFetcher, BatchConfig
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保项目路径正确，并且所有依赖模块都已安装")
    sys.exit(1)


class TestBatchConfig(unittest.TestCase):
    """测试批量配置类"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = BatchConfig()
        
        self.assertEqual(config.start_date, "20050104")
        self.assertEqual(config.max_workers, 8)
        self.assertEqual(config.batch_size, 50)
        self.assertTrue(config.enable_checkpoint)
        self.assertEqual(config.primary_keys, ["股票代码", "日期"])
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = BatchConfig(
            max_workers=16,
            batch_size=100,
            enable_checkpoint=False
        )
        
        self.assertEqual(config.max_workers, 16)
        self.assertEqual(config.batch_size, 100)
        self.assertFalse(config.enable_checkpoint)


class TestBatchHistoricalFetcher(unittest.TestCase):
    """测试基础版批量获取器"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.checkpoint_file = os.path.join(self.temp_dir, "test_checkpoint.json")
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('fetcher.batch.batch_historical_fetcher.PostgreSQLManager')
    @patch('fetcher.batch.batch_historical_fetcher.RedisManager')
    def test_initialization(self, mock_redis, mock_db):
        """测试初始化"""
        fetcher = BatchHistoricalFetcher(
            max_workers=4,
            batch_size=10
        )
        
        self.assertEqual(fetcher.max_workers, 4)
        self.assertEqual(fetcher.batch_size, 10)
        self.assertTrue(hasattr(fetcher, 'checkpoint_file'))
    
    def test_calculate_date_range(self):
        """测试日期范围计算"""
        with patch('fetcher.batch.batch_historical_fetcher.PostgreSQLManager'), \
             patch('fetcher.batch.batch_historical_fetcher.RedisManager'):
            
            fetcher = BatchHistoricalFetcher()
            
            # 测试无历史数据的情况
            start_date, end_date = fetcher.calculate_date_range(None)
            self.assertEqual(start_date, "20050104")
            
            # 测试有历史数据的情况
            last_date = "20231201"
            start_date, end_date = fetcher.calculate_date_range(last_date)
            self.assertEqual(start_date, "20231202")
    
    def test_preprocess_data(self):
        """测试数据预处理"""
        with patch('fetcher.batch.batch_historical_fetcher.PostgreSQLManager'), \
             patch('fetcher.batch.batch_historical_fetcher.RedisManager'):
            
            fetcher = BatchHistoricalFetcher()
            
            # 创建测试数据
            test_data = pd.DataFrame({
                '日期': ['2023-12-01', '2023-12-02'],
                '开盘': [10.0, 11.0],
                '收盘': [10.5, 11.5],
                '最高': [10.8, 11.8],
                '最低': [9.8, 10.8],
                '成交量': [1000000, 1100000]
            })
            
            processed_data = fetcher._preprocess_data(test_data, "000001")
            
            # 检查股票代码是否添加
            self.assertIn('股票代码', processed_data.columns)
            self.assertTrue(all(processed_data['股票代码'] == "000001"))
            
            # 检查日期格式
            self.assertEqual(processed_data['日期'].dtype, 'object')


class TestEnhancedBatchFetcher(unittest.TestCase):
    """测试增强版批量获取器"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.yaml")
        
        # 创建测试配置文件
        test_config = """
basic:
  start_date: "20230101"
  enable_checkpoint: true
  log_level: "INFO"

concurrency:
  max_workers: 2
  batch_size: 5
  request_interval: 0.0

validation:
  enable_data_validation: true
  check_duplicates: true
        """
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            f.write(test_config)
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('fetcher.batch.enhanced_batch_fetcher.PostgreSQLManager')
    @patch('fetcher.batch.enhanced_batch_fetcher.RedisManager')
    def test_config_loading(self, mock_redis, mock_db):
        """测试配置文件加载"""
        fetcher = EnhancedBatchFetcher(config_file=self.config_file)
        
        self.assertEqual(fetcher.config.start_date, "20230101")
        self.assertEqual(fetcher.config.max_workers, 2)
        self.assertEqual(fetcher.config.batch_size, 5)
        self.assertTrue(fetcher.config.enable_data_validation)
    
    def test_data_validation(self):
        """测试数据验证"""
        with patch('fetcher.batch.enhanced_batch_fetcher.PostgreSQLManager'), \
             patch('fetcher.batch.enhanced_batch_fetcher.RedisManager'):
            
            fetcher = EnhancedBatchFetcher(config_file=self.config_file)
            
            # 测试正常数据
            good_data = pd.DataFrame({
                '日期': ['2023-12-01', '2023-12-02'],
                '股票代码': ['000001', '000001'],
                '开盘': [10.0, 11.0],
                '收盘': [10.5, 11.5],
                '最高': [10.8, 11.8],
                '最低': [9.8, 10.8],
                '成交量': [1000000, 1100000]
            })
            
            is_valid, errors = fetcher.validate_data(good_data, "000001")
            self.assertTrue(is_valid)
            self.assertEqual(len(errors), 0)
            
            # 测试异常数据（最高价小于最低价）
            bad_data = pd.DataFrame({
                '日期': ['2023-12-01'],
                '股票代码': ['000001'],
                '开盘': [10.0],
                '收盘': [10.5],
                '最高': [9.0],  # 最高价小于最低价
                '最低': [9.8],
                '成交量': [1000000]
            })
            
            is_valid, errors = fetcher.validate_data(bad_data, "000001")
            self.assertFalse(is_valid)
            self.assertGreater(len(errors), 0)
    
    def test_data_preprocessing(self):
        """测试数据预处理"""
        with patch('fetcher.batch.enhanced_batch_fetcher.PostgreSQLManager'), \
             patch('fetcher.batch.enhanced_batch_fetcher.RedisManager'):
            
            fetcher = EnhancedBatchFetcher(config_file=self.config_file)
            
            # 创建包含异常值的测试数据
            test_data = pd.DataFrame({
                '日期': ['2023-12-01', '2023-12-02', '2023-12-01'],  # 包含重复
                '开盘': [10.0, -1.0, 10.0],  # 包含负数
                '收盘': [10.5, 11.5, 10.5],
                '最高': [10.8, 11.8, 10.8],
                '最低': [9.8, 10.8, 9.8],
                '成交量': [1000000, -100, 1000000]  # 包含负数
            })
            
            processed_data = fetcher._preprocess_data_enhanced(test_data, "000001")
            
            # 检查重复数据是否被移除
            self.assertEqual(len(processed_data), 2)
            
            # 检查负数价格是否被处理
            self.assertTrue(processed_data['开盘'].isna().any() or (processed_data['开盘'] > 0).all())
            
            # 检查负数成交量是否被处理为0
            self.assertTrue((processed_data['成交量'] >= 0).all())


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('akshare.stock_zh_a_hist')
    @patch('fetcher.batch.batch_historical_fetcher.PostgreSQLManager')
    @patch('fetcher.batch.batch_historical_fetcher.RedisManager')
    def test_basic_fetcher_integration(self, mock_redis, mock_db, mock_akshare):
        """测试基础版获取器集成"""
        # 模拟akshare返回数据
        mock_data = pd.DataFrame({
            '日期': ['2023-12-01', '2023-12-02'],
            '开盘': [10.0, 11.0],
            '收盘': [10.5, 11.5],
            '最高': [10.8, 11.8],
            '最低': [9.8, 10.8],
            '成交量': [1000000, 1100000],
            '成交额': [10500000, 12650000],
            '振幅': [10.0, 9.1],
            '涨跌幅': [5.0, 9.5],
            '涨跌额': [0.5, 1.0],
            '换手率': [1.0, 1.1]
        })
        mock_akshare.return_value = mock_data
        
        # 模拟数据库操作
        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance
        mock_db_instance.query.return_value = [
            {'股票代码': '000001'},
            {'股票代码': '000002'}
        ]
        mock_db_instance.upsert_from_df.return_value = True
        
        # 创建获取器并运行测试
        fetcher = BatchHistoricalFetcher(
            max_workers=1,
            batch_size=2
        )
        
        # 测试单只股票处理
        result = fetcher.process_single_stock("000001")
        
        self.assertIsInstance(result, dict)
        self.assertIn("不复权", result)
        self.assertIn("后复权", result)


def run_performance_test():
    """运行性能测试"""
    print("\n" + "="*60)
    print("性能测试")
    print("="*60)
    
    # 测试数据预处理性能
    print("\n测试数据预处理性能...")
    
    # 创建大量测试数据
    large_data = pd.DataFrame({
        '日期': pd.date_range('2020-01-01', periods=1000),
        '开盘': range(1000),
        '收盘': range(1000),
        '最高': range(1000),
        '最低': range(1000),
        '成交量': range(1000)
    })
    
    with patch('fetcher.batch.enhanced_batch_fetcher.PostgreSQLManager'), \
         patch('fetcher.batch.enhanced_batch_fetcher.RedisManager'):
        
        fetcher = EnhancedBatchFetcher()
        
        start_time = time.time()
        processed_data = fetcher._preprocess_data_enhanced(large_data, "000001")
        end_time = time.time()
        
        print(f"处理 {len(large_data)} 条记录耗时: {end_time - start_time:.4f} 秒")
        print(f"处理后记录数: {len(processed_data)}")
        print(f"平均每条记录耗时: {(end_time - start_time) / len(large_data) * 1000:.4f} 毫秒")


def run_connectivity_test():
    """运行连接性测试"""
    print("\n" + "="*60)
    print("连接性测试")
    print("="*60)
    
    # 测试数据库连接
    print("\n测试数据库连接...")
    try:
        from db import PostgreSQLManager
        db = PostgreSQLManager()
        result = db.query("SELECT 1 as test")
        if result:
            print("✅ 数据库连接正常")
        else:
            print("❌ 数据库连接失败")
        db.close()
    except Exception as e:
        print(f"❌ 数据库连接异常: {e}")
    
    # 测试Redis连接
    print("\n测试Redis连接...")
    try:
        from db import RedisManager
        redis = RedisManager()
        redis.set_value("test_key", "test_value", expire=10)
        value = redis.get_value("test_key")
        if value == "test_value":
            print("✅ Redis连接正常")
        else:
            print("❌ Redis连接失败")
        redis.delete("test_key")
        redis.close()
    except Exception as e:
        print(f"❌ Redis连接异常: {e}")
    
    # 测试akshare连接
    print("\n测试akshare连接...")
    try:
        import akshare as ak
        # 获取一只股票的少量数据进行测试
        df = ak.stock_zh_a_hist(
            symbol="000001",
            period="daily",
            start_date="20231201",
            end_date="20231201",
            adjust=""
        )
        if not df.empty:
            print("✅ akshare连接正常")
        else:
            print("⚠️  akshare连接正常但无数据返回")
    except Exception as e:
        print(f"❌ akshare连接异常: {e}")


def run_sample_test():
    """运行示例测试"""
    print("\n" + "="*60)
    print("示例测试 - 获取少量股票数据")
    print("="*60)
    
    try:
        # 使用基础版获取器测试
        print("\n使用基础版获取器测试...")
        fetcher = BatchHistoricalFetcher(
            max_workers=1,
            batch_size=2
        )
        
        # 测试获取2只股票的数据
        test_stocks = ["000001", "000002"]
        print(f"测试股票: {test_stocks}")
        
        # 这里只是测试初始化，不实际运行获取
        print("✅ 基础版获取器初始化成功")
        fetcher.cleanup()
        
        # 使用增强版获取器测试
        print("\n使用增强版获取器测试...")
        enhanced_fetcher = EnhancedBatchFetcher()
        print("✅ 增强版获取器初始化成功")
        enhanced_fetcher.cleanup()
        
        print("\n✅ 所有示例测试通过")
        
    except Exception as e:
        print(f"❌ 示例测试失败: {e}")


def main():
    """主函数"""
    print("批量股票历史数据获取工具 - 测试脚本")
    print("="*60)
    
    # 运行单元测试
    print("\n运行单元测试...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # 运行性能测试
    run_performance_test()
    
    # 运行连接性测试
    run_connectivity_test()
    
    # 运行示例测试
    run_sample_test()
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
    print("\n如果所有测试都通过，说明批量获取工具已准备就绪。")
    print("你可以使用以下命令开始批量获取:")
    print("  python fetcher/batch/run_batch_update.py --dry-run")
    print("  python fetcher/batch/run_batch_update.py --mode enhanced")


if __name__ == "__main__":
    main()