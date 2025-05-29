#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
表结构管理器测试脚本

用于测试表结构管理器的功能，包括检查表结构完整性、自动修复表结构和提供数据填充指导
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent)  # db/test_table_structure_manager.py -> stock-a
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入表结构管理器
from db.table_structure_manager import TableStructureManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TableStructureManagerTest')


def test_check_table_structure():
    """测试检查表结构完整性功能"""
    manager = TableStructureManager()
    
    # 测试检查股票技术指标表
    stock_result = manager.check_table_structure("股票技术指标")
    logger.info(f"股票技术指标表检查结果: {stock_result['message']}")
    
    # 测试检查行业技术指标表
    industry_result = manager.check_table_structure("行业技术指标")
    logger.info(f"行业技术指标表检查结果: {industry_result['message']}")
    
    # 测试检查指数技术指标表
    index_result = manager.check_table_structure("指数技术指标")
    logger.info(f"指数技术指标表检查结果: {index_result['message']}")
    
    return stock_result, industry_result, index_result


def test_fix_table_structure(tables):
    """测试修复表结构功能
    
    Args:
        tables (list): 需要修复的表名列表
    """
    manager = TableStructureManager()
    
    for table in tables:
        # 检查表结构
        check_result = manager.check_table_structure(table)
        
        if not check_result['complete'] and check_result['exists']:
            # 修复表结构
            fix_result = manager.fix_table_structure(table)
            logger.info(f"表 {table} 修复结果: {fix_result['message']}")
            
            # 如果有添加的列，提供填充指导
            if fix_result['added_columns']:
                logger.info(f"表 {table} 新增列数据填充指导:")
                for col_name, col_type in fix_result['added_columns']:
                    guidance = manager.get_column_data_fill_guidance(table, col_name)
                    logger.info(f"  列 {col_name} ({col_type}):")
                    logger.info(f"    表行数: {guidance['row_count']}")
                    logger.info(f"    主键: {', '.join(guidance['primary_key'])}")
                    logger.info(f"    SQL示例:")
                    for example in guidance['examples']:
                        logger.info(f"      {example['description']}:")
                        logger.info(f"      {example['sql']}")
        else:
            logger.info(f"表 {table} 无需修复: {check_result['message']}")


def test_add_indicator_columns():
    """测试添加技术指标列功能"""
    manager = TableStructureManager()
    
    # 定义要添加的技术指标
    indicators = {
        "ATR14": {"类型": "double precision", "表": ["股票技术指标", "行业技术指标", "指数技术指标"]},
        "ATR20": {"类型": "double precision", "表": ["股票技术指标", "行业技术指标", "指数技术指标"]},
        "HIGHEST_20": {"类型": "double precision", "表": ["股票技术指标", "行业技术指标", "指数技术指标"]},
        "HIGHEST_55": {"类型": "double precision", "表": ["股票技术指标", "行业技术指标", "指数技术指标"]},
        "LOWEST_10": {"类型": "double precision", "表": ["股票技术指标", "行业技术指标", "指数技术指标"]},
        "LOWEST_20": {"类型": "double precision", "表": ["股票技术指标", "行业技术指标", "指数技术指标"]}
    }
    
    # 添加技术指标列
    results = manager.add_indicator_columns(indicators)
    
    # 输出结果
    logger.info(f"添加技术指标列结果: 成功 {results['成功']}，失败 {results['失败']}，已存在 {results['已存在']}")
    
    # 输出详细结果
    for indicator, table_results in results['详情'].items():
        logger.info(f"指标 {indicator} 添加结果:")
        for table, result in table_results.items():
            status = result['状态']
            reason = result.get('原因', '')
            logger.info(f"  表 {table}: {status} {reason}")
    
    return results


def main():
    """主函数"""
    logger.info("开始测试表结构管理器...")
    
    # 测试检查表结构完整性
    stock_result, industry_result, index_result = test_check_table_structure()
    
    # 确定需要修复的表
    tables_to_fix = []
    if not stock_result['complete'] and stock_result['exists']:
        tables_to_fix.append("股票技术指标")
    if not industry_result['complete'] and industry_result['exists']:
        tables_to_fix.append("行业技术指标")
    if not index_result['complete'] and index_result['exists']:
        tables_to_fix.append("指数技术指标")
    
    # 测试修复表结构
    if tables_to_fix:
        logger.info(f"需要修复的表: {', '.join(tables_to_fix)}")
        test_fix_table_structure(tables_to_fix)
    else:
        logger.info("所有表结构完整，无需修复")
    
    # 测试添加技术指标列
    logger.info("测试添加技术指标列...")
    test_add_indicator_columns()
    
    logger.info("表结构管理器测试完成")


if __name__ == "__main__":
    main()