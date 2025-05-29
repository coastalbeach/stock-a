#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
复权因子更新程序

该程序用于获取和更新股票的复权因子，并确保后复权数据的准确性。
主要功能：
1. 从akshare获取股票的不复权和后复权数据
2. 计算并更新复权因子表
3. 检测并清除错误的复权数据
4. 支持定期检查复权系数变更

注意：复权价格计算公式为 复权价格 = a * 不复权价格 + b
"""

import os
import sys
import time
import datetime
import logging
import pandas as pd
import numpy as np
import akshare as ak
import psycopg2
import psycopg2.extras
from tqdm import tqdm
import concurrent.futures
import json
import traceback

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入项目模块
from data.fetcher.stock.historical_data import StockHistoricalData
from utils.db_manager import PostgreSQLManager
from utils.logger import LoggerManager


class AdjustmentFactorUpdater:
    """复权因子更新器
    
    该类用于计算和更新股票的复权因子，并确保后复权数据的准确性。
    """
    
    def __init__(self):
        """初始化复权因子更新器"""
        # 初始化日志
        logger_manager = LoggerManager()
        self.logger = logger_manager.get_logger("adjustment_factor")
        
        # 初始化数据库连接
        self.db = PostgreSQLManager()
        
        # 初始化历史数据获取器（用于获取正确的数据）
        self.hist_data = StockHistoricalData()
        
        # 设置默认参数
        self.start_date = "20100101"  # 默认起始日期
        self.check_days = 30  # 默认检查最近30天的数据
        
        # 获取最新交易日
        self.last_trading_day = self._get_last_trading_day()
        if self.last_trading_day:
            self.last_trading_day_str = pd.to_datetime(self.last_trading_day).strftime("%Y%m%d")
        else:
            self.last_trading_day_str = datetime.datetime.now().strftime("%Y%m%d")
    
    def _get_last_trading_day(self):
        """获取最新交易日
        
        Returns:
            str: 最新交易日，格式为YYYY-MM-DD
        """
        try:
            # 从数据库获取最新交易日
            sql = "SELECT MAX(\"日期\") FROM \"股票历史行情_不复权\""
            result = self.db.query_one(sql)
            if result and result[0]:
                return result[0].strftime("%Y-%m-%d")
            
            # 如果数据库没有数据，则使用akshare获取
            tool_trade_date_hist_sina_df = ak.tool_trade_date_hist_sina()
            if not tool_trade_date_hist_sina_df.empty:
                latest_date = tool_trade_date_hist_sina_df.iloc[-1, 0]
                return latest_date
            
            return None
        except Exception as e:
            self.logger.error(f"获取最新交易日失败: {e}")
            return None
    
    def create_adjustment_factor_table_if_not_exists(self):
        """创建复权因子表（如果不存在）
        
        Returns:
            bool: 是否成功创建表
        """
        try:
            # 创建复权因子表
            sql = """
            CREATE TABLE IF NOT EXISTS public."复权因子表" (
                "股票代码" varchar(10) NOT NULL,
                "日期" date NOT NULL,
                "前复权因子" double precision,
                "后复权因子" double precision,
                "更新时间" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT "复权因子表_pkey" PRIMARY KEY ("股票代码", "日期")
            )
            """
            self.db.execute(sql)
            
            # 创建索引
            index_sql = "CREATE INDEX IF NOT EXISTS idx_adjustment_factor_date ON \"复权因子表\" (\"日期\")"
            self.db.execute(index_sql)
            
            self.logger.info("复权因子表创建完成")
            return True
        except Exception as e:
            self.logger.error(f"创建复权因子表失败: {e}")
            return False
    
    def get_stock_list(self):
        """获取股票列表
        
        Returns:
            list: 股票代码列表
        """
        try:
            # 从数据库获取股票列表
            sql = "SELECT DISTINCT \"股票代码\" FROM \"股票历史行情_不复权\""
            result = self.db.query(sql)
            if result:
                return [row[0] for row in result]
            
            # 如果数据库没有数据，则使用akshare获取
            stock_info_a_code_name_df = ak.stock_info_a_code_name()
            if not stock_info_a_code_name_df.empty:
                return stock_info_a_code_name_df["code"].tolist()
            
            return []
        except Exception as e:
            self.logger.error(f"获取股票列表失败: {e}")
            return []
    
    def get_last_dividend_date(self, stock_code):
        """获取股票最近的除权除息日期
        
        Args:
            stock_code (str): 股票代码
            
        Returns:
            str: 最近的除权除息日期，格式为YYYYMMDD，如果没有则返回None
        """
        try:
            # 从数据库获取最近的除权除息日期
            sql = "SELECT MAX(\"除权除息日期\") FROM \"除权除息信息\" WHERE \"股票代码\" = %s"
            result = self.db.query_one(sql, (stock_code,))
            if result and result[0]:
                return result[0].strftime("%Y%m%d")
            
            return None
        except Exception as e:
            self.logger.debug(f"获取{stock_code}最近的除权除息日期失败: {e}")
            return None
    
    def calculate_adjustment_factors(self, stock_code, start_date=None, end_date=None):
        """计算股票的复权因子
        
        Args:
            stock_code (str): 股票代码
            start_date (str, optional): 开始日期，格式为YYYYMMDD
            end_date (str, optional): 结束日期，格式为YYYYMMDD
            
        Returns:
            pandas.DataFrame: 复权因子数据，包含股票代码、日期、前复权因子、后复权因子
        """
        try:
            # 设置默认日期
            if not start_date:
                start_date = self.start_date
            if not end_date:
                end_date = self.last_trading_day_str
            
            # 获取不复权数据
            self.logger.debug(f"获取{stock_code}的不复权数据")
            df_no_adjust = self.hist_data.fetch_stock_history(stock_code, start_date, end_date, adjust="")
            if df_no_adjust is None or df_no_adjust.empty:
                self.logger.warning(f"获取{stock_code}的不复权数据失败")
                return None
            
            # 获取后复权数据
            self.logger.debug(f"获取{stock_code}的后复权数据")
            df_hfq = self.hist_data.fetch_stock_history(stock_code, start_date, end_date, adjust="hfq")
            if df_hfq is None or df_hfq.empty:
                self.logger.warning(f"获取{stock_code}的后复权数据失败")
                return None
            
            # 确保日期格式一致
            df_no_adjust["日期"] = pd.to_datetime(df_no_adjust["日期"])
            df_hfq["日期"] = pd.to_datetime(df_hfq["日期"])
            
            # 合并数据
            df_merged = pd.merge(df_no_adjust, df_hfq, on=["股票代码", "日期"], suffixes=('_原始', '_复权'))
            
            # 计算后复权因子 (复权价格 = 后复权因子 * 不复权价格)
            # 使用收盘价计算复权因子
            df_merged["后复权因子"] = df_merged["收盘_复权"] / df_merged["收盘_原始"]
            
            # 计算前复权因子 (前复权因子 = 最新的后复权因子 / 当前的后复权因子)
            latest_factor = df_merged.iloc[-1]["后复权因子"]
            df_merged["前复权因子"] = latest_factor / df_merged["后复权因子"]
            
            # 创建结果DataFrame
            result_df = pd.DataFrame({
                "股票代码": df_merged["股票代码"],
                "日期": df_merged["日期"],
                "前复权因子": df_merged["前复权因子"],
                "后复权因子": df_merged["后复权因子"]
            })
            
            return result_df
        except Exception as e:
            self.logger.error(f"计算{stock_code}的复权因子失败: {e}")
            return None
    
    def save_adjustment_factors(self, df):
        """保存复权因子到数据库
        
        Args:
            df (pandas.DataFrame): 复权因子数据
            
        Returns:
            bool: 是否保存成功
        """
        if df is None or df.empty:
            self.logger.warning("没有复权因子数据需要保存")
            return False
        
        try:
            # 准备数据
            records = df.to_dict('records')
            
            # 构建SQL语句
            columns = ["股票代码", "日期", "前复权因子", "后复权因子"]
            placeholders = ", ".join([f"%({col})s" for col in columns])
            columns_str = ", ".join([f"\"{ col}\"" for col in columns])
            
            sql = f"""
            INSERT INTO \"复权因子表\" ({columns_str})
            VALUES ({placeholders})
            ON CONFLICT (\"股票代码\", \"日期\")
            DO UPDATE SET 
                \"前复权因子\" = EXCLUDED.\"前复权因子\",
                \"后复权因子\" = EXCLUDED.\"后复权因子\",
                \"更新时间\" = CURRENT_TIMESTAMP
            """
            
            # 执行批量插入
            with self.db.conn.cursor() as cursor:
                psycopg2.extras.execute_batch(cursor, sql, records)
            self.db.conn.commit()
            
            self.logger.info(f"成功保存{len(records)}条复权因子数据")
            return True
        except Exception as e:
            self.db.conn.rollback()
            self.logger.error(f"保存复权因子数据失败: {e}")
            return False
    
    def check_and_fix_hfq_data(self, stock_code, last_dividend_date=None):
        """检查并修复后复权数据
        
        Args:
            stock_code (str): 股票代码
            last_dividend_date (str, optional): 最近的除权除息日期，格式为YYYYMMDD
            
        Returns:
            bool: 是否成功修复数据
        """
        try:
            # 如果没有提供除权除息日期，则获取最近的除权除息日期
            if not last_dividend_date:
                last_dividend_date = self.get_last_dividend_date(stock_code)
            
            # 如果没有除权除息日期，则检查最近30天的数据
            if not last_dividend_date:
                check_date = (datetime.datetime.now() - datetime.timedelta(days=self.check_days)).strftime("%Y%m%d")
            else:
                check_date = last_dividend_date
            
            self.logger.debug(f"检查{stock_code}从{check_date}开始的后复权数据")
            
            # 删除从check_date开始的后复权数据
            sql = """
            DELETE FROM \"股票历史行情_后复权\" 
            WHERE \"股票代码\" = %s AND \"日期\" >= %s
            """
            self.db.execute(sql, (stock_code, check_date))
            
            # 重新计算复权因子
            factors_df = self.calculate_adjustment_factors(stock_code, check_date, self.last_trading_day_str)
            if factors_df is not None and not factors_df.empty:
                # 保存复权因子
                self.save_adjustment_factors(factors_df)
                
                # 触发器会自动更新后复权数据，无需手动更新
                self.logger.info(f"成功修复{stock_code}的后复权数据")
                return True
            
            self.logger.warning(f"无法修复{stock_code}的后复权数据，因为无法计算复权因子")
            return False
        except Exception as e:
            self.logger.error(f"修复{stock_code}的后复权数据失败: {e}")
            return False
    
    def update_stock_adjustment_factors(self, stock_code):
        """更新单只股票的复权因子
        
        Args:
            stock_code (str): 股票代码
            
        Returns:
            bool: 是否更新成功
        """
        try:
            # 获取最近的除权除息日期
            last_dividend_date = self.get_last_dividend_date(stock_code)
            
            # 检查并修复后复权数据
            return self.check_and_fix_hfq_data(stock_code, last_dividend_date)
        except Exception as e:
            self.logger.error(f"更新{stock_code}的复权因子失败: {e}")
            return False
    
    def run(self, limit=None):
        """运行复权因子更新流程

        Args:
            limit (int, optional): 限制处理的股票数量，用于测试。默认为None，表示处理所有股票。
        """
        try:
            self.logger.info("开始运行复权因子更新流程")
            
            # 创建复权因子表（如果不存在）
            self.create_adjustment_factor_table_if_not_exists()
            
            # 获取股票列表
            stock_list = self.get_stock_list()
            if not stock_list:
                self.logger.error("没有获取到股票列表，无法更新数据")
                return
            
            # 如果设置了limit，则只选择部分股票用于调试
            if limit is not None and isinstance(limit, int) and limit > 0:
                stock_list = stock_list[:limit]
                self.logger.info(f"调试模式：仅处理前 {limit} 只股票")

            # 更新复权因子（使用并行处理提高效率）
            self.logger.info(f"开始更新{len(stock_list)}只股票的复权因子")
            success_count = 0
            failed_count = 0
            
            # 使用线程池并行处理
            max_workers = min(12, len(stock_list))  # 最多12个线程
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                future_to_stock = {executor.submit(self.update_stock_adjustment_factors, stock_code): stock_code for stock_code in stock_list}
                
                # 处理结果
                for future in tqdm(concurrent.futures.as_completed(future_to_stock), total=len(stock_list), desc="更新复权因子"):
                    stock_code = future_to_stock[future]
                    try:
                        if future.result():
                            success_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        self.logger.error(f"更新{stock_code}的复权因子时发生异常: {e}")
                        failed_count += 1
            
            self.logger.info(f"复权因子更新完成，成功更新{success_count}/{len(stock_list)}只股票，失败{failed_count}只")
            
            self.logger.info("复权因子更新流程完成")
        except Exception as e:
            self.logger.error(f"运行复权因子更新流程失败: {e}")
            traceback.print_exc()
        finally:
            # 关闭数据库连接
            self.db.close()


def main():
    """主函数"""
    # 记录开始时间
    start_time = time.time()
    
    # 初始化日志
    logger_manager = LoggerManager()
    logger = logger_manager.get_logger("adjustment_factor")
    
    try:
        logger.info("=== 开始运行复权因子更新程序 ===")
        
        # 解析命令行参数
        import argparse
        parser = argparse.ArgumentParser(description="复权因子更新程序")
        parser.add_argument("--limit", type=int, help="限制处理的股票数量，用于测试")
        parser.add_argument("--stock", type=str, help="指定要处理的单只股票代码")
        parser.add_argument("--check-days", type=int, default=30, help="检查最近多少天的数据，默认30天")
        args = parser.parse_args()
        
        # 创建AdjustmentFactorUpdater实例
        updater = AdjustmentFactorUpdater()
        updater.check_days = args.check_days
        
        # 如果指定了单只股票，则只处理该股票
        if args.stock:
            logger.info(f"仅处理股票: {args.stock}")
            updater.update_stock_adjustment_factors(args.stock)
        else:
            # 否则运行完整流程
            updater.run(args.limit)
        
        # 记录结束时间和运行时间
        end_time = time.time()
        run_time = end_time - start_time
        logger.info(f"程序运行完成，耗时: {run_time:.2f}秒")
        logger.info("=== 复权因子更新程序运行结束 ===")
    except Exception as e:
        logger.error(f"程序运行异常: {e}")
        logger.error("=== 复权因子更新程序异常终止 ===")
        traceback.print_exc()


if __name__ == "__main__":
    main()