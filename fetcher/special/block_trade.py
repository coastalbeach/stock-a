#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
大宗交易数据获取模块

获取A股市场大宗交易数据，包括每日明细数据，支持按日期范围查询
数据来源：AKShare接口
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import time

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent.parent) # fetcher/special/block_trade.py -> stock-a
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入数据存储模块
from db import PostgreSQLManager, RedisManager

# 导入AKShare
import akshare as ak


class BlockTrade:
    """大宗交易数据获取类
    
    负责获取A股市场大宗交易数据，包括每日明细数据，并存储到数据库
    """
    
    def __init__(self):
        """初始化大宗交易数据获取类"""
        self.pg_manager = PostgreSQLManager()
        self.redis_manager = RedisManager()
        
        # Redis键前缀
        self.redis_block_trade_prefix = "大宗交易:"
        self.redis_update_time_key = "大宗交易:更新时间"
        
        # 数据过期时间（秒）
        self.block_trade_expire = 86400  # 24小时
    
    def create_block_trade_table(self):
        """创建大宗交易数据表"""
        try:
            # 创建表SQL
            columns_dict = {
                "序号": "INTEGER",
                "交易日期": "DATE NOT NULL",
                "证券代码": "VARCHAR(10) NOT NULL",
                "证券简称": "VARCHAR(50) NOT NULL",
                "成交价": "FLOAT",
                "成交量": "FLOAT",
                "成交额": "FLOAT",
                "溢价率": "FLOAT",
                "买方营业部": "TEXT",
                "卖方营业部": "TEXT",
                "证券类型": "VARCHAR(10)",  # A股、B股等
                "更新时间": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "PRIMARY KEY": "(交易日期, 证券代码, 序号)"
            }
            
            # 创建表
            self.pg_manager.create_table("大宗交易", columns_dict)
            
            # 创建索引
            self.pg_manager.create_index("大宗交易", "idx_block_trade_date", ["交易日期"])
            self.pg_manager.create_index("大宗交易", "idx_block_trade_code", ["证券代码"])
            
            print("大宗交易数据表创建成功")
            return True
        except Exception as e:
            print(f"创建大宗交易数据表失败: {e}")
            return False
    
    def fetch_block_trade_daily(self, symbol="A股", start_date=None, end_date=None):
        """获取每日大宗交易明细数据
        
        Args:
            symbol (str, optional): 证券类型，可选值："A股"、"B股"，默认为"A股"
            start_date (str, optional): 开始日期，格式："20220101"，默认为None，表示获取最近一个交易日数据
            end_date (str, optional): 结束日期，格式："20220101"，默认为None，表示获取到最近一个交易日数据
            
        Returns:
            pandas.DataFrame: 大宗交易明细数据
        """
        try:
            # 如果未指定日期，设置为最近一个交易日
            if not start_date:
                start_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y%m%d")
            
            # 构建Redis键
            redis_key = f"{self.redis_block_trade_prefix}{symbol}:{start_date}_{end_date}"
            
            # 尝试从Redis获取缓存数据
            cached_data = self.redis_manager.get_value(redis_key)
            if cached_data is not None:
                print(f"从Redis获取{symbol}大宗交易数据: {start_date} - {end_date}")
                return pd.DataFrame(cached_data)
            
            # 从AKShare获取数据
            print(f"从AKShare获取{symbol}大宗交易数据: {start_date} - {end_date}")
            df = ak.stock_dzjy_mrmx(symbol=symbol, start_date=start_date, end_date=end_date)
            
            if df.empty:
                print(f"未获取到{symbol}大宗交易数据")
                return pd.DataFrame()
            
            # 添加证券类型列
            df["证券类型"] = symbol
            
            # 处理日期格式
            if "交易日期" in df.columns:
                df["交易日期"] = pd.to_datetime(df["交易日期"]).dt.date
            
            # 添加更新时间列
            df["更新时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 转换为字典并缓存到Redis
            data_dict = df.to_dict(orient="records")
            self.redis_manager.set_value(redis_key, data_dict, expire=self.block_trade_expire)
            
            # 更新最后更新时间
            self.redis_manager.set_value(f"{self.redis_update_time_key}:{symbol}", 
                                  datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                  expire=self.block_trade_expire)
            
            # 保存到PostgreSQL
            self._save_block_trade_to_postgresql(df)
            
            return df
        except Exception as e:
            print(f"获取{symbol}大宗交易数据失败: {e}")
            return pd.DataFrame()
    
    def _save_block_trade_to_postgresql(self, df):
        """将大宗交易数据保存到PostgreSQL
        
        Args:
            df (pandas.DataFrame): 大宗交易数据
        """
        if df.empty:
            print("大宗交易数据为空，跳过保存")
            return
        
        try:
            # 确保表存在
            if not self.pg_manager.table_exists("大宗交易"):
                self.create_block_trade_table()
            
            # 保存数据
            conflict_columns = ["交易日期", "证券代码", "序号"]
            update_columns = [col for col in df.columns if col not in conflict_columns]
            
            self.pg_manager.insert_df("大宗交易", df, conflict_columns, update_columns)
            print(f"成功保存{len(df)}条大宗交易数据到PostgreSQL")
        except Exception as e:
            print(f"保存大宗交易数据到PostgreSQL失败: {e}")
    
    def get_block_trade_by_date(self, date):
        """根据日期获取大宗交易数据
        
        Args:
            date (str): 日期，格式："20220101"
            
        Returns:
            pandas.DataFrame: 大宗交易数据
        """
        try:
            # 格式化日期
            date_str = date.replace("-", "")
            
            # 从数据库获取数据
            sql = """
            SELECT * FROM "大宗交易"
            WHERE "交易日期" = %s
            ORDER BY "成交额" DESC
            """
            
            df = self.pg_manager.query_df(sql, (date_str,))
            
            if df.empty:
                # 如果数据库中没有数据，尝试从AKShare获取
                print(f"数据库中未找到{date}的大宗交易数据，尝试从AKShare获取")
                df = self.fetch_block_trade_daily(start_date=date_str, end_date=date_str)
            
            return df
        except Exception as e:
            print(f"获取{date}大宗交易数据失败: {e}")
            return pd.DataFrame()
    
    def get_block_trade_by_code(self, code, start_date=None, end_date=None):
        """根据证券代码获取大宗交易数据
        
        Args:
            code (str): 证券代码
            start_date (str, optional): 开始日期，格式："20220101"，默认为None，表示获取最近30天数据
            end_date (str, optional): 结束日期，格式："20220101"，默认为None，表示获取到最新数据
            
        Returns:
            pandas.DataFrame: 大宗交易数据
        """
        try:
            # 如果未指定日期，设置默认值
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y%m%d")
            
            # 从数据库获取数据
            sql = """
            SELECT * FROM "大宗交易"
            WHERE "证券代码" = %s
            AND "交易日期" BETWEEN %s AND %s
            ORDER BY "交易日期" DESC, "成交额" DESC
            """
            
            # 格式化日期
            start_date_fmt = datetime.strptime(start_date, "%Y%m%d").date()
            end_date_fmt = datetime.strptime(end_date, "%Y%m%d").date()
            
            df = self.pg_manager.query_df(sql, (code, start_date_fmt, end_date_fmt))
            
            if df.empty:
                # 如果数据库中没有数据，尝试从AKShare获取全部数据再筛选
                print(f"数据库中未找到{code}的大宗交易数据，尝试从AKShare获取")
                all_df = self.fetch_block_trade_daily(start_date=start_date, end_date=end_date)
                if not all_df.empty:
                    df = all_df[all_df["证券代码"] == code]
            
            return df
        except Exception as e:
            print(f"获取{code}大宗交易数据失败: {e}")
            return pd.DataFrame()
    
    def get_block_trade_statistics(self, start_date=None, end_date=None, top_n=20):
        """获取大宗交易统计数据
        
        Args:
            start_date (str, optional): 开始日期，格式："20220101"，默认为None，表示获取最近30天数据
            end_date (str, optional): 结束日期，格式："20220101"，默认为None，表示获取到最新数据
            top_n (int, optional): 返回前N条记录，默认为20
            
        Returns:
            dict: 包含多个统计DataFrame的字典
        """
        try:
            # 如果未指定日期，设置默认值
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y%m%d")
            
            # 格式化日期
            start_date_fmt = datetime.strptime(start_date, "%Y%m%d").date()
            end_date_fmt = datetime.strptime(end_date, "%Y%m%d").date()
            
            # 1. 成交额最大的股票
            sql_amount = """
            SELECT "证券代码", "证券简称", SUM("成交额") as "总成交额", COUNT(*) as "成交次数"
            FROM "大宗交易"
            WHERE "交易日期" BETWEEN %s AND %s
            GROUP BY "证券代码", "证券简称"
            ORDER BY "总成交额" DESC
            LIMIT %s
            """
            df_amount = self.pg_manager.query_df(sql_amount, (start_date_fmt, end_date_fmt, top_n))
            
            # 2. 成交次数最多的股票
            sql_count = """
            SELECT "证券代码", "证券简称", COUNT(*) as "成交次数", SUM("成交额") as "总成交额"
            FROM "大宗交易"
            WHERE "交易日期" BETWEEN %s AND %s
            GROUP BY "证券代码", "证券简称"
            ORDER BY "成交次数" DESC
            LIMIT %s
            """
            df_count = self.pg_manager.query_df(sql_count, (start_date_fmt, end_date_fmt, top_n))
            
            # 3. 溢价率最高的交易
            sql_premium = """
            SELECT "交易日期", "证券代码", "证券简称", "成交价", "成交量", "成交额", "溢价率", "买方营业部", "卖方营业部"
            FROM "大宗交易"
            WHERE "交易日期" BETWEEN %s AND %s
            ORDER BY "溢价率" DESC
            LIMIT %s
            """
            df_premium = self.pg_manager.query_df(sql_premium, (start_date_fmt, end_date_fmt, top_n))
            
            # 4. 折价率最高的交易
            sql_discount = """
            SELECT "交易日期", "证券代码", "证券简称", "成交价", "成交量", "成交额", "溢价率", "买方营业部", "卖方营业部"
            FROM "大宗交易"
            WHERE "交易日期" BETWEEN %s AND %s
            ORDER BY "溢价率" ASC
            LIMIT %s
            """
            df_discount = self.pg_manager.query_df(sql_discount, (start_date_fmt, end_date_fmt, top_n))
            
            # 返回统计结果
            return {
                "成交额最大": df_amount,
                "成交次数最多": df_count,
                "溢价率最高": df_premium,
                "折价率最高": df_discount
            }
        except Exception as e:
            print(f"获取大宗交易统计数据失败: {e}")
            return {}


if __name__ == "__main__":
    # 测试代码
    block_trade = BlockTrade()
    
    # 创建表
    block_trade.create_block_trade_table()
    
    # 获取最近一天的大宗交易数据
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    df = block_trade.fetch_block_trade_daily(start_date=yesterday, end_date=yesterday)
    print(f"获取到{len(df)}条大宗交易数据")
    
    # 获取统计数据
    stats = block_trade.get_block_trade_statistics()
    for key, value in stats.items():
        print(f"\n{key}统计:")
        if not value.empty:
            print(value.head(5))