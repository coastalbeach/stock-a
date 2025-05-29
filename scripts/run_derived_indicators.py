# -*- coding: utf-8 -*-

"""
衍生指标计算系统运行脚本

此脚本用于运行衍生指标计算系统，支持以下功能：
1. 计算指定实体类型（股票、行业、指数）的衍生指标
2. 支持批量处理多个实体
3. 支持指定日期范围
4. 支持干运行模式（不写入数据库）

使用示例：
    # 计算所有股票的衍生指标
    python run_derived_indicators.py --type stock
    
    # 计算指定股票的衍生指标
    python run_derived_indicators.py --type stock --ids 000001,000002
    
    # 计算指定行业的衍生指标，指定日期范围
    python run_derived_indicators.py --type industry --ids 计算机,金融 --start 2023-01-01 --end 2023-12-31
    
    # 干运行模式（不写入数据库）
    python run_derived_indicators.py --type index --ids 000300,000905 --dry-run
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入项目模块
from core.analyzer.derived_indicators import DerivedIndicatorCalculator
from utils.config_loader import load_connection_config


def parse_arguments():
    """解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(description='运行衍生指标计算系统')
    
    # 实体类型
    parser.add_argument('--type', '-t', type=str, choices=['stock', 'industry', 'index', 'all'],
                        default='all', help='实体类型 (stock, industry, index, all)')
    
    # 实体ID列表
    parser.add_argument('--ids', '-i', type=str, default=None,
                        help='实体ID列表，用逗号分隔，例如：000001,000002')
    
    # 开始日期
    parser.add_argument('--start', '-s', type=str, default=None,
                        help='开始日期，格式：YYYY-MM-DD')
    
    # 结束日期
    parser.add_argument('--end', '-e', type=str, default=None,
                        help='结束日期，格式：YYYY-MM-DD')
    
    # 干运行模式
    parser.add_argument('--dry-run', '-d', action='store_true',
                        help='干运行模式，不写入数据库')
    
    # 显示详细日志
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='显示详细日志')
    
    return parser.parse_args()


def run_derived_indicators(args):
    """运行衍生指标计算
    
    Args:
        args (argparse.Namespace): 命令行参数
    """
    # 设置日志级别
    import logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 加载数据库配置
    db_config = load_connection_config()
    
    # 创建计算器实例
    calculator = DerivedIndicatorCalculator(db_config=db_config, dry_run=args.dry_run)
    
    # 处理日期范围
    end_date = args.end if args.end else datetime.now().strftime('%Y-%m-%d')
    start_date = args.start if args.start else (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    # 处理实体类型和ID
    if args.type == 'all':
        data_types = ['stock', 'industry', 'index']
    else:
        data_types = [args.type]
    
    # 如果指定了ID列表，则只处理这些实体
    entity_ids_map = None
    if args.ids:
        entity_ids = args.ids.split(',')
        entity_ids_map = {args.type: entity_ids}
    
    # 打印运行信息
    print(f"\n{'='*50}")
    print(f"衍生指标计算系统运行参数：")
    print(f"实体类型: {', '.join(data_types)}")
    print(f"实体ID: {entity_ids_map if entity_ids_map else '所有'}")
    print(f"日期范围: {start_date} 至 {end_date}")
    print(f"干运行模式: {'是' if args.dry_run else '否'}")
    print(f"{'='*50}\n")
    
    # 运行计算
    try:
        if entity_ids_map:
            # 处理指定实体
            for entity_type in data_types:
                if entity_type in entity_ids_map:
                    for entity_id in entity_ids_map[entity_type]:
                        print(f"处理 {entity_type} {entity_id}...")
                        calculator.process_entity(entity_type, entity_id, start_date, end_date)
        else:
            # 处理所有实体
            print(f"处理所有 {', '.join(data_types)} 实体...")
            calculator.run(data_types=data_types)
        
        print("\n计算完成！")
        if args.dry_run:
            print("注意：这是干运行模式，结果未写入数据库。")
            
    except Exception as e:
        print(f"\n计算过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    args = parse_arguments()
    sys.exit(run_derived_indicators(args))