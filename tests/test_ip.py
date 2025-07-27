#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试IP被封问题修复

测试修改后的历史数据获取模块是否能正确处理网络连接问题
"""

import sys
from pathlib import Path

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from fetcher.stock.historical_data import StockHistoricalData

def test_single_stock():
    """测试单只股票数据获取"""
    print("=== 测试单只股票数据获取 ===")
    
    try:
        # 创建数据获取实例
        fetcher = StockHistoricalData()
        
        # 测试获取单只股票数据（以平安银行000001为例）
        stock_code = "000001"
        start_date = "20250101"
        end_date = "20250121"
        
        print(f"正在获取股票{stock_code}从{start_date}到{end_date}的历史数据...")
        
        # 测试不复权数据
        df_no_adjust = fetcher.fetch_stock_history(stock_code, start_date, end_date, adjust="")
        if df_no_adjust is not None and not df_no_adjust.empty:
            print(f"✓ 成功获取不复权数据，共{len(df_no_adjust)}条记录")
            print(df_no_adjust.head())
        else:
            print("✗ 获取不复权数据失败")
        
        # 测试后复权数据
        df_hfq = fetcher.fetch_stock_history(stock_code, start_date, end_date, adjust="hfq")
        if df_hfq is not None and not df_hfq.empty:
            print(f"✓ 成功获取后复权数据，共{len(df_hfq)}条记录")
            print(df_hfq.head())
        else:
            print("✗ 获取后复权数据失败")
            
    except Exception as e:
        print(f"✗ 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()

def test_latest_data():
    """测试最新行情数据获取"""
    print("\n=== 测试最新行情数据获取 ===")
    
    try:
        # 创建数据获取实例
        fetcher = StockHistoricalData()
        
        print("正在获取最新行情数据...")
        
        # 测试获取最新行情数据
        df_latest = fetcher.fetch_latest_data()
        if df_latest is not None and not df_latest.empty:
            print(f"✓ 成功获取最新行情数据，共{len(df_latest)}只股票")
            print(df_latest.head())
        else:
            print("✗ 获取最新行情数据失败")
            
    except Exception as e:
        print(f"✗ 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()

def test_limited_run():
    """测试限制数量的完整运行"""
    print("\n=== 测试限制数量的完整运行 ===")
    
    try:
        # 创建数据获取实例
        fetcher = StockHistoricalData()
        
        print("正在运行限制数量的完整数据更新流程（仅处理前5只股票）...")
        
        # 运行限制数量的更新流程
        fetcher.run(limit=5)
        
        print("✓ 完整运行测试完成")
            
    except Exception as e:
        print(f"✗ 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主测试函数"""
    print("开始测试IP被封问题修复...")
    
    # 测试单只股票数据获取
    test_single_stock()
    
    # 测试最新行情数据获取
    test_latest_data()
    
    # 测试限制数量的完整运行
    test_limited_run()
    
    print("\n=== 所有测试完成 ===")

if __name__ == "__main__":
    main()