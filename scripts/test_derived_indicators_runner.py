# -*- coding: utf-8 -*-

"""
衍生指标计算器测试运行脚本

提供一种简单的方式来测试衍生指标计算器在不同情况下的表现。
这个脚本可以直接从命令行运行，不依赖于单元测试框架。
"""

import os
import sys
from pathlib import Path
import logging
import argparse

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入衍生指标计算器
from core.analyzer.derived_indicators import DerivedIndicatorCalculator

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_test_cases():
    """
    运行一系列测试用例来验证衍生指标计算器的功能
    """
    logger.info("开始运行衍生指标计算器测试用例")
    
    # 初始化计算器（使用dry_run模式，不写入数据库）
    calculator = DerivedIndicatorCalculator(dry_run=True)
    
    # 测试用例1：处理单个股票
    logger.info("\n测试用例1：处理单个股票")
    calculator.process_entity('stock', '000001', '2023-01-01', '2023-01-31')
    
    # 测试用例2：处理单个行业
    logger.info("\n测试用例2：处理单个行业")
    calculator.process_entity('industry', '计算机', '2023-01-01', '2023-01-31')
    
    # 测试用例3：处理单个指数
    logger.info("\n测试用例3：处理单个指数")
    calculator.process_entity('index', '000300', '2023-01-01', '2023-01-31')
    
    # 测试用例4：批量处理多个实体
    logger.info("\n测试用例4：批量处理多个实体")
    specific_entities = {
        'stock': ['000001', '600000'],
        'industry': ['计算机', '金融'],
        'index': ['000300', '000905']
    }
    calculator.run(data_types=['stock', 'industry', 'index'], specific_entities=specific_entities)
    
    # 测试用例5：使用不同的日期范围
    logger.info("\n测试用例5：使用不同的日期范围")
    calculator.process_entity('stock', '000001', '2022-01-01', '2022-12-31')
    
    # 测试用例6：处理不存在的实体
    logger.info("\n测试用例6：处理不存在的实体")
    calculator.process_entity('stock', '999999', '2023-01-01', '2023-01-31')
    
    logger.info("衍生指标计算器测试用例运行完成")

def run_custom_test(entity_type, entity_ids, start_date, end_date):
    """
    运行自定义测试
    
    Args:
        entity_type (str): 实体类型 ('stock', 'industry', 'index')
        entity_ids (list): 实体ID列表
        start_date (str): 开始日期
        end_date (str): 结束日期
    """
    logger.info(f"开始运行自定义测试：{entity_type} - {entity_ids}")
    
    # 初始化计算器（使用dry_run模式，不写入数据库）
    calculator = DerivedIndicatorCalculator(dry_run=True)
    
    # 创建specific_entities字典
    specific_entities = {entity_type: entity_ids}
    
    # 运行计算
    calculator.run(data_types=[entity_type], specific_entities=specific_entities)
    
    logger.info("自定义测试运行完成")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="测试衍生指标计算器")
    parser.add_argument("--run-all", action="store_true", help="运行所有预定义的测试用例")
    parser.add_argument("--entity-type", type=str, choices=['stock', 'industry', 'index'], help="实体类型")
    parser.add_argument("--entity-ids", nargs="+", help="实体ID列表")
    parser.add_argument("--start-date", type=str, help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end-date", type=str, help="结束日期 YYYY-MM-DD")
    
    args = parser.parse_args()
    
    if args.run_all:
        run_test_cases()
    elif args.entity_type and args.entity_ids:
        run_custom_test(args.entity_type, args.entity_ids, args.start_date, args.end_date)
    else:
        parser.print_help()