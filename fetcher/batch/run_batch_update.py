#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
批量股票历史数据更新运行脚本

提供简单的命令行接口来运行批量更新任务
支持不同的运行模式和参数配置
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import List, Optional

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from fetcher.batch.enhanced_batch_fetcher import EnhancedBatchFetcher
from fetcher.batch.batch_historical_fetcher import BatchHistoricalFetcher


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="批量股票历史数据更新工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python run_batch_update.py --mode enhanced                    # 使用增强版批量获取器
  python run_batch_update.py --mode basic --workers 4          # 使用基础版，4个线程
  python run_batch_update.py --stocks 000001,000002            # 只更新指定股票
  python run_batch_update.py --config custom_config.yaml       # 使用自定义配置文件
  python run_batch_update.py --no-checkpoint                   # 不使用断点续传
        """
    )
    
    parser.add_argument(
        "--mode", 
        choices=["basic", "enhanced"], 
        default="enhanced",
        help="选择批量获取器模式 (默认: enhanced)"
    )
    
    parser.add_argument(
        "--config", 
        type=str,
        help="配置文件路径 (仅适用于enhanced模式)"
    )
    
    parser.add_argument(
        "--stocks", 
        type=str,
        help="指定股票代码列表，用逗号分隔 (例如: 000001,000002,600000)"
    )
    
    parser.add_argument(
        "--workers", 
        type=int,
        default=8,
        help="并发线程数 (默认: 8)"
    )
    
    parser.add_argument(
        "--batch-size", 
        type=int,
        default=50,
        help="批处理大小 (默认: 50)"
    )
    
    parser.add_argument(
        "--no-checkpoint", 
        action="store_true",
        help="禁用断点续传功能"
    )
    
    parser.add_argument(
        "--start-date", 
        type=str,
        help="开始日期 (格式: YYYYMMDD，默认: 20050104)"
    )
    
    parser.add_argument(
        "--log-level", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
        default="INFO",
        help="日志级别 (默认: INFO)"
    )
    
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="试运行模式，只显示将要处理的股票列表，不实际执行"
    )
    
    parser.add_argument(
        "--output-report", 
        type=str,
        help="保存执行报告到指定文件"
    )
    
    return parser.parse_args()


def parse_stock_list(stocks_str: str) -> List[str]:
    """解析股票代码列表字符串
    
    Args:
        stocks_str (str): 逗号分隔的股票代码字符串
        
    Returns:
        List[str]: 股票代码列表
    """
    if not stocks_str:
        return []
    
    stock_list = []
    for stock in stocks_str.split(','):
        stock = stock.strip()
        if stock:
            # 确保股票代码格式正确
            if len(stock) == 6 and stock.isdigit():
                stock_list.append(stock)
            else:
                print(f"警告: 股票代码格式不正确: {stock}")
    
    return stock_list


def run_basic_mode(args) -> dict:
    """运行基础模式批量获取
    
    Args:
        args: 命令行参数
        
    Returns:
        dict: 执行结果
    """
    print("使用基础版批量获取器...")
    
    # 解析股票列表
    stock_list = None
    if args.stocks:
        stock_list = parse_stock_list(args.stocks)
        if not stock_list:
            return {"success": False, "message": "没有有效的股票代码"}
        print(f"指定股票列表: {stock_list}")
    
    # 创建基础版获取器
    fetcher = BatchHistoricalFetcher(
        max_workers=args.workers,
        batch_size=args.batch_size,
        start_date=args.start_date or "20050104"
    )
    
    try:
        # 运行批量更新
        if args.dry_run:
            if stock_list is None:
                stock_list = fetcher.get_stock_list()
            print(f"\n试运行模式: 将处理 {len(stock_list)} 只股票")
            print(f"股票代码: {', '.join(stock_list[:10])}{'...' if len(stock_list) > 10 else ''}")
            return {"success": True, "message": "试运行完成", "total_stocks": len(stock_list)}
        else:
            result = fetcher.run_batch_update(
                stock_list=stock_list,
                use_checkpoint=not args.no_checkpoint
            )
            return result
    
    finally:
        fetcher.cleanup()


def run_enhanced_mode(args) -> dict:
    """运行增强模式批量获取
    
    Args:
        args: 命令行参数
        
    Returns:
        dict: 执行结果
    """
    print("使用增强版批量获取器...")
    
    # 解析股票列表
    stock_list = None
    if args.stocks:
        stock_list = parse_stock_list(args.stocks)
        if not stock_list:
            return {"success": False, "message": "没有有效的股票代码"}
        print(f"指定股票列表: {stock_list}")
    
    # 创建增强版获取器
    fetcher = EnhancedBatchFetcher(config_file=args.config)
    
    try:
        # 运行批量更新
        if args.dry_run:
            if stock_list is None:
                stock_list = fetcher.get_filtered_stock_list()
            print(f"\n试运行模式: 将处理 {len(stock_list)} 只股票")
            print(f"股票代码: {', '.join(stock_list[:10])}{'...' if len(stock_list) > 10 else ''}")
            return {"success": True, "message": "试运行完成", "total_stocks": len(stock_list)}
        else:
            result = fetcher.run_enhanced_batch_update(
                stock_list=stock_list,
                use_checkpoint=not args.no_checkpoint
            )
            return result
    
    finally:
        fetcher.cleanup()


def save_report(result: dict, output_file: str):
    """保存执行报告到文件
    
    Args:
        result (dict): 执行结果
        output_file (str): 输出文件路径
    """
    try:
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 保存报告
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n执行报告已保存到: {output_file}")
        
    except Exception as e:
        print(f"保存执行报告失败: {e}")


def print_result_summary(result: dict):
    """打印结果摘要
    
    Args:
        result (dict): 执行结果
    """
    print("\n" + "="*60)
    print("批量更新执行结果摘要")
    print("="*60)
    
    if result.get("success"):
        print(f"✅ 执行状态: 成功")
        
        if "total_stocks" in result:
            print(f"📊 总股票数: {result['total_stocks']}")
        
        if "completed_stocks" in result:
            print(f"✅ 成功更新: {result['completed_stocks']}")
        
        if "failed_stocks" in result:
            print(f"❌ 失败数量: {result['failed_stocks']}")
        
        if "success_rate" in result:
            print(f"📈 成功率: {result['success_rate']:.2f}%")
        
        if "duration_seconds" in result:
            duration = result['duration_seconds']
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = int(duration % 60)
            print(f"⏱️  总耗时: {hours:02d}:{minutes:02d}:{seconds:02d}")
        
        if "average_time_per_stock" in result:
            print(f"⚡ 平均每只股票耗时: {result['average_time_per_stock']:.2f}秒")
        
        if result.get("failed_stock_list"):
            failed_stocks = result['failed_stock_list']
            print(f"\n❌ 失败的股票 ({len(failed_stocks)}只):")
            # 分行显示，每行10个
            for i in range(0, len(failed_stocks), 10):
                batch = failed_stocks[i:i+10]
                print(f"   {', '.join(batch)}")
    else:
        print(f"❌ 执行状态: 失败")
        print(f"💬 错误信息: {result.get('message', '未知错误')}")
    
    print("="*60)


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    print("批量股票历史数据更新工具")
    print(f"运行模式: {args.mode}")
    print(f"并发线程数: {args.workers}")
    print(f"批处理大小: {args.batch_size}")
    print(f"断点续传: {'禁用' if args.no_checkpoint else '启用'}")
    print(f"日志级别: {args.log_level}")
    
    if args.dry_run:
        print("⚠️  试运行模式: 不会实际执行数据更新")
    
    print("-" * 60)
    
    try:
        # 根据模式运行相应的批量获取器
        if args.mode == "basic":
            result = run_basic_mode(args)
        else:  # enhanced
            result = run_enhanced_mode(args)
        
        # 打印结果摘要
        print_result_summary(result)
        
        # 保存报告（如果指定了输出文件）
        if args.output_report:
            save_report(result, args.output_report)
        
        # 返回适当的退出码
        if result.get("success"):
            print("\n🎉 批量更新任务完成!")
            sys.exit(0)
        else:
            print("\n💥 批量更新任务失败!")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断了批量更新任务")
        sys.exit(130)
    
    except Exception as e:
        print(f"\n💥 批量更新过程中发生异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()