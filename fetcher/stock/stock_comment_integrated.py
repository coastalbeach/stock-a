#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
千股千评数据一体化获取与存储程序

本程序一次性获取指定股票的千股千评全部数据，并整合存储到尽量少的数据表中
专注于数据获取功能，提高数据获取和存储效率
"""

import sys
import os
import pandas as pd
from datetime import datetime
import argparse
import time

# 添加项目根目录到系统路径
from pathlib import Path
project_root = str(Path(__file__).parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入自定义模块
from data.fetcher.special.stock_comment import get_stock_comment_all
from data.storage.postgresql_manager import PostgreSQLManager
from utils.logger import LoggerManager

# 设置日志
logger_manager = LoggerManager()
logger = logger_manager.get_logger('stock_qian_gu_qian_ping')


def create_integrated_tables(pg_manager):
    """
    创建整合后的千股千评数据表
    
    :param pg_manager: PostgreSQL管理器实例
    """
    # 创建日度数据整合表（包含每日更新的指标）
    pg_manager.execute("""
    CREATE TABLE IF NOT EXISTS 千股千评_日度数据 (
        股票代码 VARCHAR(10) NOT NULL,
        交易日 DATE NOT NULL,
        机构参与度 NUMERIC(10, 2),
        评分 NUMERIC(10, 2),
        用户关注指数 NUMERIC(10, 2),
        当日意愿上升 NUMERIC(10, 2),
        五日平均参与意愿变化 NUMERIC(10, 2),
        市场成本 NUMERIC(10, 2),
        五日市场成本 NUMERIC(10, 2),
        更新时间 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (股票代码, 交易日)
    )
    """)
    
    # 创建分钟级数据表（用于存储市场参与意愿的分钟级数据）
    pg_manager.execute("""
    CREATE TABLE IF NOT EXISTS 千股千评_分钟数据 (
        股票代码 VARCHAR(10) NOT NULL,
        日期时间 TIMESTAMP NOT NULL,
        大户参与意愿 NUMERIC(10, 2),
        全部参与意愿 NUMERIC(10, 2),
        散户参与意愿 NUMERIC(10, 2),
        更新时间 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (股票代码, 日期时间)
    )
    """)
    
    logger.info("千股千评整合数据表创建完成")


def save_integrated_data(pg_manager, symbol, data_dict):
    """
    将千股千评数据整合保存到数据库
    
    :param pg_manager: PostgreSQL管理器实例
    :param symbol: 股票代码
    :param data_dict: 千股千评数据字典
    """
    # 1. 处理日度数据
    daily_data = []
    dates = set()
    
    # 收集所有日期
    if "机构参与度" in data_dict and not data_dict["机构参与度"].empty:
        for date in data_dict["机构参与度"]["交易日"]:
            dates.add(date)
    
    if "历史评分" in data_dict and not data_dict["历史评分"].empty:
        for date in data_dict["历史评分"]["交易日"]:
            dates.add(date)
    
    if "用户关注指数" in data_dict and not data_dict["用户关注指数"].empty:
        for date in data_dict["用户关注指数"]["交易日"]:
            dates.add(date)
    
    if "日度市场参与意愿" in data_dict and not data_dict["日度市场参与意愿"].empty:
        for date in data_dict["日度市场参与意愿"]["交易日"]:
            dates.add(date)
    
    if "市场成本" in data_dict and not data_dict["市场成本"].empty:
        for date in data_dict["市场成本"]["日期"]:
            dates.add(date)
    
    # 为每个日期创建一条记录
    for date in sorted(dates):
        record = {
            "股票代码": symbol,
            "交易日": date,
            "机构参与度": None,
            "评分": None,
            "用户关注指数": None,
            "当日意愿上升": None,
            "五日平均参与意愿变化": None,
            "市场成本": None,
            "五日市场成本": None
        }
        
        # 填充机构参与度数据
        if "机构参与度" in data_dict and not data_dict["机构参与度"].empty:
            df = data_dict["机构参与度"]
            row = df[df["交易日"] == date]
            if not row.empty:
                record["机构参与度"] = row["机构参与度"].values[0]
        
        # 填充历史评分数据
        if "历史评分" in data_dict and not data_dict["历史评分"].empty:
            df = data_dict["历史评分"]
            row = df[df["交易日"] == date]
            if not row.empty:
                record["评分"] = row["评分"].values[0]
        
        # 填充用户关注指数数据
        if "用户关注指数" in data_dict and not data_dict["用户关注指数"].empty:
            df = data_dict["用户关注指数"]
            row = df[df["交易日"] == date]
            if not row.empty:
                record["用户关注指数"] = row["用户关注指数"].values[0]
        
        # 填充日度市场参与意愿数据
        if "日度市场参与意愿" in data_dict and not data_dict["日度市场参与意愿"].empty:
            df = data_dict["日度市场参与意愿"]
            # 确保列名一致性
            if "5日平均参与意愿变化" in df.columns:
                df.rename(columns={"5日平均参与意愿变化": "五日平均参与意愿变化"}, inplace=True)
            
            row = df[df["交易日"] == date]
            if not row.empty:
                record["当日意愿上升"] = row["当日意愿上升"].values[0]
                if "五日平均参与意愿变化" in row.columns:
                    record["五日平均参与意愿变化"] = row["五日平均参与意愿变化"].values[0]
        
        # 填充市场成本数据
        if "市场成本" in data_dict and not data_dict["市场成本"].empty:
            df = data_dict["市场成本"]
            row = df[df["日期"] == date]
            if not row.empty:
                record["市场成本"] = row["市场成本"].values[0]
                record["五日市场成本"] = row["五日市场成本"].values[0]
        
        daily_data.append(record)
    
    # 将日度数据保存到数据库
    if daily_data:
        daily_df = pd.DataFrame(daily_data)
        pg_manager.insert_df(
            "千股千评_日度数据",
            daily_df,
            ["股票代码", "交易日"],
            ["机构参与度", "评分", "用户关注指数", "当日意愿上升", "五日平均参与意愿变化", "市场成本", "五日市场成本"]
        )
        logger.info(f"股票{symbol}的日度数据已保存，共{len(daily_data)}条记录")
    
    # 2. 处理分钟级数据
    if "市场参与意愿" in data_dict and not data_dict["市场参与意愿"].empty:
        minute_df = data_dict["市场参与意愿"].copy()
        minute_df.insert(0, "股票代码", symbol)
        minute_df.rename(columns={
            "大户": "大户参与意愿",
            "全部": "全部参与意愿",
            "散户": "散户参与意愿"
        }, inplace=True)
        
        pg_manager.insert_df(
            "千股千评_分钟数据",
            minute_df,
            ["股票代码", "日期时间"],
            ["大户参与意愿", "全部参与意愿", "散户参与意愿"]
        )
        logger.info(f"股票{symbol}的分钟级数据已保存，共{len(minute_df)}条记录")


def get_and_save_stock_comment(symbol, pg_manager):
    """
    获取并保存指定股票的千股千评数据
    
    :param symbol: 股票代码
    :param pg_manager: PostgreSQL管理器实例
    :return: 是否成功获取并保存数据
    """
    try:
        logger.info(f"开始获取股票{symbol}的千股千评数据")
        start_time = time.time()
        
        # 获取数据
        data_dict = get_stock_comment_all(symbol=symbol)
        
        # 保存整合数据
        save_integrated_data(pg_manager, symbol, data_dict)
        
        end_time = time.time()
        logger.info(f"股票{symbol}的千股千评数据获取与保存完成，耗时{end_time - start_time:.2f}秒")
        return True
    except Exception as e:
        logger.error(f"获取或保存股票{symbol}的千股千评数据时出错: {e}")
        return False


def main():
    """
    主函数
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="获取并整合保存千股千评数据")
    parser.add_argument("-s", "--symbols", nargs="+", help="股票代码列表，如：600000 000001 601318")
    parser.add_argument("-f", "--file", help="包含股票代码的文件路径，每行一个股票代码")
    parser.add_argument("-b", "--batch", type=int, default=10, help="批处理大小，默认为10")
    args = parser.parse_args()
    
    # 获取股票代码列表
    symbols = []
    if args.symbols:
        symbols.extend(args.symbols)
    
    if args.file and os.path.exists(args.file):
        with open(args.file, 'r', encoding='utf-8') as f:
            for line in f:
                code = line.strip()
                if code and code not in symbols:
                    symbols.append(code)
    
    # 如果没有提供股票代码，使用默认示例
    if not symbols:
        symbols = ["600000", "000001", "601318"]
    
    # 连接数据库
    pg_manager = PostgreSQLManager()
    
    try:
        # 创建数据表
        create_integrated_tables(pg_manager)
        
        # 批量处理股票
        total = len(symbols)
        success = 0
        batch_size = min(args.batch, total)
        
        logger.info(f"开始处理{total}只股票的千股千评数据，批处理大小为{batch_size}")
        
        for i in range(0, total, batch_size):
            batch = symbols[i:i+batch_size]
            logger.info(f"开始处理第{i//batch_size+1}批，共{len(batch)}只股票")
            
            for symbol in batch:
                if get_and_save_stock_comment(symbol, pg_manager):
                    success += 1
            
            logger.info(f"第{i//batch_size+1}批处理完成，当前进度: {min(i+batch_size, total)}/{total}")
        
        logger.info(f"全部处理完成，成功: {success}/{total}")
    
    except Exception as e:
        logger.error(f"执行过程中出错: {e}")
    
    finally:
        # 关闭数据库连接
        pg_manager.close()
        logger.info("数据库连接已关闭")


if __name__ == "__main__":
    main()