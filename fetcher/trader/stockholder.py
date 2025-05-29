#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
股东信息获取模块

获取A股股票的股东相关信息，包括股东户数、十大流通股东、机构持股等
属于交易者数据获取模块的一部分
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
project_root = str(Path(__file__).resolve().parent.parent.parent) # fetcher/trader/stockholder.py -> stock-a
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入数据存储模块
from db import PostgreSQLManager, RedisManager

# 导入AKShare
import akshare as ak


class StockholderData:
    """股东信息数据获取类
    
    负责获取A股市场股东相关数据，包括股东户数、十大流通股东、机构持股等，并存储到数据库
    """
    
    def __init__(self):
        """初始化股东信息数据获取类"""
        self.pg_manager = PostgreSQLManager()
        self.redis_manager = RedisManager()
        
        # Redis键前缀
        self.redis_gdhs_prefix = "股东户数:"
        self.redis_sdgd_prefix = "十大股东:"
        self.redis_sdltgd_prefix = "十大流通股东:"
        self.redis_xsjj_prefix = "限售解禁:"
        self.redis_gdzjc_prefix = "股东增减持:"
        self.redis_ggcg_prefix = "高管持股:"
        self.redis_update_time_key = "股东信息:更新时间"
        
        # 数据过期时间（秒）
        self.gdhs_expire = 86400 * 7  # 7天
        self.sdgd_expire = 86400 * 7  # 7天
        self.sdltgd_expire = 86400 * 7  # 7天
        self.xsjj_expire = 86400 * 7  # 7天
        self.gdzjc_expire = 86400 * 3  # 3天
        self.ggcg_expire = 86400 * 7  # 7天
    
    def create_gdhs_table(self):
        """创建股东户数表"""
        try:
            # 定义表结构，列名遵循中文规范，部分保留AKShare原始名称
            columns_dict = {
                "股票代码": "VARCHAR(10) NOT NULL",        # Mapped from AKShare " 代码"
                "股票简称": "VARCHAR(50) NOT NULL",        # Mapped from AKShare "名称"
                "截止日期": "DATE NOT NULL",              # Mapped from AKShare "股东户数统计截止日"
                "股东户数": "INTEGER",                   # Mapped from AKShare "股东户数-本次"
                "股东户数-增减": "INTEGER",               # 保留原始AKShare列名
                "股东户数-增减 比例": "FLOAT",            # 保留原始AKShare列名
                "总股本": "FLOAT",                       # 保留原始AKShare列名
                "户均持股数量": "FLOAT",                 # 保留原始AKShare列名
                # 定义主键
                "PRIMARY KEY": "\"股票代码\", \"截止日期\""
            }
            
            # 创建表
            self.pg_manager.create_table("股东户数", columns_dict)
            
            # 创建索引
            self.pg_manager.create_index("股东户数", "idx_gdhs_code", ["股票代码"])
            self.pg_manager.create_index("股东户数", "idx_gdhs_date", ["截止日期"])
            
            print("股东户数表结构定义成功或已存在。")
            return True
        except Exception as e:
            print(f"创建或更新股东户数表结构失败: {e}")
            return False
    
    def create_sdgd_table(self):
        """创建十大股东表"""
        try:
            # 创建表SQL
            columns_dict = {
                "股票代码": "VARCHAR(10) NOT NULL",
                "股票简称": "VARCHAR(50) NOT NULL",
                "截止日期": "DATE NOT NULL",
                "公告日期": "DATE",
                "股东名称": "TEXT NOT NULL",
                "持股数量": "FLOAT",
                "持股比例": "FLOAT",
                "股本性质": "VARCHAR(50)",
                "股东类型": "VARCHAR(50)",
                "变动情况": "VARCHAR(50)",
                "PRIMARY KEY": "股票代码, 截止日期, 股东名称"
            }
            
            # 创建表
            self.pg_manager.create_table("十大股东", columns_dict)
            
            # 创建索引
            self.pg_manager.create_index("十大股东", "idx_sdgd_code", ["股票代码"])
            self.pg_manager.create_index("十大股东", "idx_sdgd_date", ["截止日期"])
            
            return True
        except Exception as e:
            print(f"创建十大股东表失败: {e}")
            return False
    
    def create_sdltgd_table(self):
        """创建十大流通股东表"""
        try:
            # 创建表SQL
            columns_dict = {
                "股票代码": "VARCHAR(10) NOT NULL",
                "股票简称": "VARCHAR(50) NOT NULL",
                "截止日期": "DATE NOT NULL",
                "公告日期": "DATE",
                "股东名称": "TEXT NOT NULL",
                "持股数量": "FLOAT",
                "持股比例": "FLOAT",
                "股东类型": "VARCHAR(50)",
                "变动情况": "VARCHAR(50)",
                "PRIMARY KEY": "股票代码, 截止日期, 股东名称"
            }
            
            # 创建表
            self.pg_manager.create_table("十大流通股东", columns_dict)
            
            # 创建索引
            self.pg_manager.create_index("十大流通股东", "idx_sdltgd_code", ["股票代码"])
            self.pg_manager.create_index("十大流通股东", "idx_sdltgd_date", ["截止日期"])
            
            return True
        except Exception as e:
            print(f"创建十大流通股东表失败: {e}")
            return False
    
    def fetch_gdhs_detail(self, symbol):
        """获取股东户数详情数据
        
        Args:
            symbol (str): 股票代码，如000001
            
        Returns:
            pandas.DataFrame: 股东户数详情数据
        """
        try:
            # 从Redis缓存获取数据
            cache_key = f"{self.redis_gdhs_prefix}{symbol}"
            cached_data = self.redis_manager.get_value(cache_key)
            
            if cached_data is not None:
                return cached_data
            
            # 从AKShare获取数据
            df = ak.stock_zh_a_gdhs_detail_em(symbol=symbol)
            
            # 数据清洗和转换
            if not df.empty:
                # 缓存数据
                self.redis_manager.set_value(cache_key, df, expire=self.gdhs_expire)
                
                # 更新最后更新时间
                self.redis_manager.set_value(f"{self.redis_update_time_key}:股东户数", 
                                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                      expire=self.gdhs_expire)
                
                # 保存到PostgreSQL
                self._save_gdhs_to_postgresql(df)
            
            return df
        except Exception as e:
            print(f"获取股票 {symbol} 的股东户数详情数据失败: {e}")
            return pd.DataFrame()
    
    def _save_gdhs_to_postgresql(self, df):
        """将股东户数数据保存到PostgreSQL
        
        Args:
            df (pandas.DataFrame): 股东户数数据 (来自AKShare, 列名可能包含如 " 代码")
        """
        if df.empty:
            print("股东户数数据为空，跳过保存")
            return
        
        try:
            # 确保表结构符合最新定义
            if not self.pg_manager.table_exists("股东户数"):
                 self.create_gdhs_table() # Call the updated create_gdhs_table

            df_to_save = df.copy()

            # AKShare原始列名 (keys) 和它们的目标数据库列名 (values)
            # 注意：AKShare的 " 代码" 列名包含一个前导空格
            rename_map = {
                " 代码": "股票代码",
                "名称": "股票简称",
                "股东户数统计截止日": "截止日期",
                "股东户数-本次": "股东户数"
                # 以下列保留AKShare原始名称，因此不在此映射中:
                # "股东户数-增减", "股东户数-增减 比例", "总股本", "户均持股数量"
            }
            
            df_to_save.rename(columns=rename_map, inplace=True)

            # 基于 *新* 表结构定义冲突列和更新列
            # 这些是数据库中的列名
            conflict_columns = ["股票代码", "截止日期"]
            
            # 数据库表的目标列名 (与 create_gdhs_table 中的定义一致)
            db_table_columns = [
                "股票代码", "股票简称", "截止日期", "股东户数",
                "股东户数-增减", "股东户数-增减 比例", "总股本", "户均持股数量"
            ]
            
            # 筛选 df_to_save，只包括数据库表结构中定义的列
            # 确保df_to_save中的列名与db_table_columns中的列名完全匹配
            columns_to_insert = [col for col in db_table_columns if col in df_to_save.columns]
            df_for_db = df_to_save[columns_to_insert]

            if df_for_db.empty:
                print("经过列名映射和筛选后，无有效数据可保存到股东户数表。")
                return

            update_columns = [col for col in df_for_db.columns if col not in conflict_columns]
            
            self.pg_manager.insert_df("股东户数", df_for_db, conflict_columns, update_columns)
            print(f"成功保存 {len(df_for_db)} 条股东户数数据到PostgreSQL")
        except Exception as e:
            print(f"保存股东户数数据到PostgreSQL失败: {e}")
    
    def fetch_sdltgd_holding_analyse(self, date=None):
        """获取十大流通股东持股分析数据
        
        Args:
            date (str, optional): 查询日期，格式："20220101"，默认为None，表示获取最近一个报告期数据
            
        Returns:
            pandas.DataFrame: 十大流通股东持股分析数据
        """
        try:
            # 如果未指定日期，设置为最近一个报告期
            if not date:
                # 获取最近的报告期日期，通常为3月31日、6月30日、9月30日、12月31日
                now = datetime.now()
                if now.month <= 3:
                    date = f"{now.year-1}1231"
                elif now.month <= 6:
                    date = f"{now.year}0331"
                elif now.month <= 9:
                    date = f"{now.year}0630"
                else:
                    date = f"{now.year}0930"
            
            # 从Redis缓存获取数据
            cache_key = f"{self.redis_sdltgd_prefix}分析:{date}"
            cached_data = self.redis_manager.get_value(cache_key)
            
            if cached_data is not None:
                print(f"从缓存获取 {date} 的十大流通股东持股分析数据")
                return cached_data
            
            # 从AKShare获取数据
            print(f"从AKShare获取 {date} 的十大流通股东持股分析数据")
            df = ak.stock_gdfx_free_holding_analyse_em(date=date)
            
            # 数据清洗和转换
            if not df.empty:
                # 缓存数据
                self.redis_manager.set_value(cache_key, df, expire=self.sdltgd_expire)
                
                # 更新最后更新时间
                self.redis_manager.set_value(f"{self.redis_update_time_key}:十大流通股东分析", 
                                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                      expire=self.sdltgd_expire)
            
            return df
        except Exception as e:
            print(f"获取 {date} 的十大流通股东持股分析数据失败: {e}")
            return pd.DataFrame()
    
    def fetch_hsgt_individual(self, stock):
        """获取沪深港通个股持股数据
        
        Args:
            stock (str): 股票代码，如002008
            
        Returns:
            pandas.DataFrame: 沪深港通个股持股数据
        """
        try:
            # 从Redis缓存获取数据
            cache_key = f"沪深港通持股:个股:{stock}"
            cached_data = self.redis_manager.get_value(cache_key)
            
            if cached_data is not None:
                print(f"从缓存获取股票 {stock} 的沪深港通持股数据")
                return cached_data
            
            # 从AKShare获取数据
            print(f"从AKShare获取股票 {stock} 的沪深港通持股数据")
            df = ak.stock_hsgt_individual_em(stock=stock)
            
            # 数据清洗和转换
            if not df.empty:
                # 缓存数据
                self.redis_manager.set_value(cache_key, df, expire=self.sdltgd_expire)
                
                # 更新最后更新时间
                self.redis_manager.set_value(f"{self.redis_update_time_key}:沪深港通个股", 
                                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                      expire=self.sdltgd_expire)
            
            return df
        except Exception as e:
            print(f"获取股票 {stock} 的沪深港通持股数据失败: {e}")
            return pd.DataFrame()
    
    def create_xsjj_table(self):
        """创建限售解禁表"""
        try:
            # 创建限售解禁批次表
            columns_dict = {
                "代码": "VARCHAR(10) NOT NULL",
                "名称": "VARCHAR(50) NOT NULL",
                "解禁日期": "DATE NOT NULL",
                "解禁数量": "FLOAT",
                "解禁数量占总股本比例": "FLOAT",
                "解禁数量占流通股比例": "FLOAT",
                "股东数": "INTEGER",
                "股份类型": "VARCHAR(50)",
                "PRIMARY KEY": "代码, 解禁日期"
            }
            
            # 创建表
            self.pg_manager.create_table("限售解禁批次", columns_dict)
            
            # 创建索引
            self.pg_manager.create_index("限售解禁批次", "idx_xsjj_pc_code", ["代码"])
            self.pg_manager.create_index("限售解禁批次", "idx_xsjj_pc_date", ["解禁日期"])
            
            # 创建限售解禁股东表
            columns_dict = {
                "代码": "VARCHAR(10) NOT NULL",
                "名称": "VARCHAR(50) NOT NULL",
                "解禁日期": "DATE NOT NULL",
                "股东名称": "TEXT NOT NULL",
                "解禁数量": "FLOAT",
                "解禁数量占总股本比例": "FLOAT",
                "股份类型": "VARCHAR(50)",
                "PRIMARY KEY": "代码, 解禁日期, 股东名称"
            }
            
            # 创建表
            self.pg_manager.create_table("限售解禁股东", columns_dict)
            
            # 创建索引
            self.pg_manager.create_index("限售解禁股东", "idx_xsjj_gd_code", ["代码"])
            self.pg_manager.create_index("限售解禁股东", "idx_xsjj_gd_date", ["解禁日期"])
            
            return True
        except Exception as e:
            print(f"创建限售解禁表失败: {e}")
            return False
    
    def fetch_restricted_release_queue(self, date=None):
        """获取限售解禁批次数据
        
        Args:
            date (str, optional): 查询日期，格式："20220101"，默认为None，表示获取所有数据
            
        Returns:
            pandas.DataFrame: 限售解禁批次数据
        """
        try:
            # 从Redis缓存获取数据
            cache_key = f"{self.redis_xsjj_prefix}批次:{date if date else 'all'}"
            cached_data = self.redis_manager.get_value(cache_key)
            
            if cached_data is not None:
                print(f"从缓存获取限售解禁批次数据")
                return cached_data
            
            # 从AKShare获取数据
            print(f"从AKShare获取限售解禁批次数据")
            df = ak.stock_restricted_release_queue_em(date=date)
            
            # 数据清洗和转换
            if not df.empty:
                # 缓存数据
                self.redis_manager.set_value(cache_key, df, expire=self.xsjj_expire)
                
                # 更新最后更新时间
                self.redis_manager.set_value(f"{self.redis_update_time_key}:限售解禁批次", 
                                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                      expire=self.xsjj_expire)
                
                # 保存到PostgreSQL
                self._save_restricted_release_queue_to_postgresql(df)
            
            return df
        except Exception as e:
            print(f"获取限售解禁批次数据失败: {e}")
            return pd.DataFrame()
    
    def _save_restricted_release_queue_to_postgresql(self, df):
        """将限售解禁批次数据保存到PostgreSQL
        
        Args:
            df (pandas.DataFrame): 限售解禁批次数据
        """
        if df.empty:
            print("限售解禁批次数据为空，跳过保存")
            return
        
        try:
            # 确保表存在
            if not self.pg_manager.table_exists("限售解禁批次"):
                self.create_xsjj_table()
            
            # 保存数据
            conflict_columns = ["代码", "解禁日期"]
            update_columns = [col for col in df.columns if col not in conflict_columns]
            
            self.pg_manager.insert_df("限售解禁批次", df, conflict_columns, update_columns)
            print(f"成功保存{len(df)}条限售解禁批次数据到PostgreSQL")
        except Exception as e:
            print(f"保存限售解禁批次数据到PostgreSQL失败: {e}")
    
    def fetch_restricted_release_stockholder(self, symbol):
        """获取限售解禁股东数据
        
        Args:
            symbol (str): 股票代码，如600000
            
        Returns:
            pandas.DataFrame: 限售解禁股东数据
        """
        try:
            # 从Redis缓存获取数据
            cache_key = f"{self.redis_xsjj_prefix}股东:{symbol}"
            cached_data = self.redis_manager.get_value(cache_key)
            
            if cached_data is not None:
                print(f"从缓存获取股票 {symbol} 的限售解禁股东数据")
                return cached_data
            
            # 从AKShare获取数据
            print(f"从AKShare获取股票 {symbol} 的限售解禁股东数据")
            df = ak.stock_restricted_release_stockholder_em(symbol=symbol)
            
            # 数据清洗和转换
            if not df.empty:
                # 缓存数据
                self.redis_manager.set_value(cache_key, df, expire=self.xsjj_expire)
                
                # 更新最后更新时间
                self.redis_manager.set_value(f"{self.redis_update_time_key}:限售解禁股东", 
                                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                      expire=self.xsjj_expire)
                
                # 保存到PostgreSQL
                self._save_restricted_release_stockholder_to_postgresql(df, symbol)
            
            return df
        except Exception as e:
            print(f"获取股票 {symbol} 的限售解禁股东数据失败: {e}")
            return pd.DataFrame()
    
    def _save_restricted_release_stockholder_to_postgresql(self, df, symbol):
        """将限售解禁股东数据保存到PostgreSQL
        
        Args:
            df (pandas.DataFrame): 限售解禁股东数据
            symbol (str): 股票代码
        """
        if df.empty:
            print("限售解禁股东数据为空，跳过保存")
            return
        
        try:
            # 确保表存在
            if not self.pg_manager.table_exists("限售解禁股东"):
                self.create_xsjj_table()
            
            # 保存数据
            conflict_columns = ["代码", "解禁日期", "股东名称"]
            update_columns = [col for col in df.columns if col not in conflict_columns]
            
            self.pg_manager.insert_df("限售解禁股东", df, conflict_columns, update_columns)
            print(f"成功保存{len(df)}条限售解禁股东数据到PostgreSQL")
        except Exception as e:
            print(f"保存限售解禁股东数据到PostgreSQL失败: {e}")
    
    def get_upcoming_restricted_release(self, days=30, min_ratio=1.0):
        """获取即将解禁的股票
        
        Args:
            days (int, optional): 未来天数，默认为30天
            min_ratio (float, optional): 最小解禁比例，默认为1.0%
            
        Returns:
            pandas.DataFrame: 即将解禁的股票数据
        """
        try:
            # 计算日期范围
            start_date = datetime.now().strftime("%Y-%m-%d")
            end_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
            
            # 构建SQL查询
            sql = f"""
            SELECT * FROM \"限售解禁批次\"  
            WHERE \"解禁日期\" >= '{start_date}' AND \"解禁日期\" <= '{end_date}'
            AND \"解禁数量占总股本比例\" >= {min_ratio}
            ORDER BY \"解禁日期\" ASC, \"解禁数量占总股本比例\" DESC
            """
            
            # 执行查询
            df = self.pg_manager.query_df(sql)
            
            if df.empty:
                # 如果数据库中没有数据，尝试从AKShare获取
                print(f"数据库中未找到即将解禁的股票数据，尝试从AKShare获取")
                df = self.fetch_restricted_release_queue()
                
                # 再次查询
                df = self.pg_manager.query_df(sql)
            
            return df
        except Exception as e:
            print(f"获取即将解禁的股票数据失败: {e}")
            return pd.DataFrame()
    
    def create_gdzjc_table(self):
        """创建股东增减持表"""
        try:
            # 创建股东增减持明细表
            columns_dict = {
                "股票代码": "VARCHAR(10) NOT NULL",
                "股票简称": "VARCHAR(50) NOT NULL",
                "公告日期": "DATE NOT NULL",
                "股东名称": "TEXT NOT NULL",
                "变动截止日期": "DATE",
                "变动价格": "FLOAT",
                "变动数量": "FLOAT",
                "变动后持股数": "FLOAT",
                "变动后持股比例": "FLOAT",
                "变动类型": "VARCHAR(20)",  # 增持、减持
                "股东类型": "VARCHAR(50)",  # 高管、实控人等
                "PRIMARY KEY": "股票代码, 公告日期, 股东名称"
            }
            
            # 创建表
            self.pg_manager.create_table("股东增减持", columns_dict)
            
            # 创建索引
            self.pg_manager.create_index("股东增减持", "idx_gdzjc_code", ["股票代码"])
            self.pg_manager.create_index("股东增减持", "idx_gdzjc_date", ["公告日期"])
            self.pg_manager.create_index("股东增减持", "idx_gdzjc_type", ["变动类型"])
            return True
        except Exception as e:
            print(f"创建股东增减持表失败: {e}")
            return False
    
    def create_ggcg_table(self):
        """创建高管持股表"""
        try:
            # 创建高管持股表
            columns_dict = {
                "股票代码": "VARCHAR(10) NOT NULL",
                "股票简称": "VARCHAR(50) NOT NULL",
                "高管姓名": "VARCHAR(50) NOT NULL",
                "职务": "VARCHAR(100)",
                "持股数": "FLOAT",
                "占总股本比例": "FLOAT",
                "持股变动数": "FLOAT",
                "变动比例": "FLOAT",
                "变动日期": "DATE NOT NULL",
                "变动原因": "TEXT",
                "PRIMARY KEY": "股票代码, 高管姓名, 变动日期"
            }
            
            # 创建表
            self.pg_manager.create_table("高管持股", columns_dict)
            
            # 创建索引
            self.pg_manager.create_index("高管持股", "idx_ggcg_code", ["股票代码"])
            self.pg_manager.create_index("高管持股", "idx_ggcg_date", ["变动日期"])
            return True
        except Exception as e:
            print(f"创建高管持股表失败: {e}")
            return False
    
    def fetch_stock_em_ggcg(self):
        """获取高管持股数据
        
        获取所有高管持股变动数据
            
        Returns:
            pandas.DataFrame: 高管持股数据
        """
        try:
            # 从Redis缓存获取数据
            cache_key = f"{self.redis_ggcg_prefix}all"
            cached_data = self.redis_manager.get_value(cache_key)
            
            if cached_data is not None:
                print(f"从缓存获取高管持股数据")
                return cached_data
            
            # 从AKShare获取数据
            print(f"从AKShare获取高管持股数据")
            # 使用正确的API：stock_hold_management_detail_em获取高管持股变动
            # 该函数不接受参数
            df = ak.stock_hold_management_detail_em()
            
            # 数据清洗和转换
            if not df.empty:
                # 缓存数据
                self.redis_manager.set_value(cache_key, df, expire=self.ggcg_expire)
                
                # 更新最后更新时间
                self.redis_manager.set_value(f"{self.redis_update_time_key}:高管持股", 
                                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                      expire=self.ggcg_expire)
                
                # 保存到PostgreSQL
                self._save_ggcg_to_postgresql(df)
            
            return df
        except Exception as e:
            print(f"获取高管持股数据失败: {e}")
            return pd.DataFrame()
    
    def _save_ggcg_to_postgresql(self, df):
        """将高管持股数据保存到PostgreSQL
        
        Args:
            df (pandas.DataFrame): 高管持股数据
        """
        if df.empty:
            print("高管持股数据为空，跳过保存")
            return
        
        try:
            # 确保表存在
            if not self.pg_manager.table_exists("高管持股"):
                self.create_ggcg_table()
            
            # 保存数据
            conflict_columns = ["股票代码", "高管姓名", "变动日期"]
            update_columns = [col for col in df.columns if col not in conflict_columns]
            
            self.pg_manager.insert_df("高管持股", df, conflict_columns, update_columns)
            print(f"成功保存{len(df)}条高管持股数据到PostgreSQL")
        except Exception as e:
            print(f"保存高管持股数据到PostgreSQL失败: {e}")
    
    def fetch_stock_em_gdzjc(self, symbol, name):
        """获取股东增减持数据
        
        Args:
            symbol (str): 股票代码，如600000
            name (str): 高管名称，如"张三"
            
        Returns:
            pandas.DataFrame: 股东增减持数据
        """
        try:
            # 从Redis缓存获取数据
            cache_key = f"{self.redis_gdzjc_prefix}{symbol}:{name}"
            cached_data = self.redis_manager.get_value(cache_key)
            
            if cached_data is not None:
                print(f"从缓存获取股票 {symbol} 高管 {name} 的股东增减持数据")
                return cached_data
            
            # 从AKShare获取数据
            print(f"从AKShare获取股票 {symbol} 高管 {name} 的股东增减持数据")
            # 使用正确的API：stock_hold_management_person_em获取股东增减持数据
            # 该函数需要symbol和name两个参数
            df = ak.stock_hold_management_person_em(symbol=symbol, name=name)
            
            # 数据清洗和转换
            if not df.empty:
                # 缓存数据
                self.redis_manager.set_value(cache_key, df, expire=self.gdzjc_expire)
                
                # 更新最后更新时间
                self.redis_manager.set_value(f"{self.redis_update_time_key}:股东增减持", 
                                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                      expire=self.gdzjc_expire)
                
                # 保存到PostgreSQL
                self._save_gdzjc_to_postgresql(df)
            
            return df
        except Exception as e:
            print(f"获取股东增减持数据失败: {e}")
            return pd.DataFrame()
    
    def _save_gdzjc_to_postgresql(self, df):
        """将股东增减持数据保存到PostgreSQL
        
        Args:
            df (pandas.DataFrame): 股东增减持数据
        """
        if df.empty:
            print("股东增减持数据为空，跳过保存")
            return
        
        try:
            # 确保表存在
            if not self.pg_manager.table_exists("股东增减持"):
                self.create_gdzjc_table()
            
            # 保存数据
            conflict_columns = ["股票代码", "公告日期", "股东名称"]
            update_columns = [col for col in df.columns if col not in conflict_columns]
            
            self.pg_manager.insert_df("股东增减持", df, conflict_columns, update_columns)
            print(f"成功保存{len(df)}条股东增减持数据到PostgreSQL")
        except Exception as e:
            print(f"保存股东增减持数据到PostgreSQL失败: {e}")
    
    def get_recent_gdzjc(self, days=30, change_type=None, min_ratio=1.0):
        """获取近期股东增减持数据
        
        Args:
            days (int, optional): 近期天数，默认为30天
            change_type (str, optional): 变动类型，可选值："增持"、"减持"，默认为None表示全部
            min_ratio (float, optional): 最小变动比例，默认为1.0%
            
        Returns:
            pandas.DataFrame: 近期股东增减持数据
        """
        try:
            # 计算日期范围
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")
            
            # 构建SQL查询条件
            conditions = [f"\"公告日期\" >= '{start_date}'"]
            
            if change_type:
                conditions.append(f"\"变动类型\" = '{change_type}'")
            
            if min_ratio > 0:
                conditions.append(f"ABS(\"变动后持股比例\") >= {min_ratio}")
            
            # 构建SQL查询
            sql = f"""
            SELECT * FROM \"股东增减持\"  
            WHERE {' AND '.join(conditions)}
            ORDER BY \"公告日期\" DESC, ABS(\"变动后持股比例\") DESC
            """
            
            # 执行查询
            df = self.pg_manager.query_df(sql)
            
            if df.empty:
                # 如果数据库中没有数据，尝试从AKShare获取
                print(f"数据库中未找到近期股东增减持数据，尝试从AKShare获取")
                start_date_fmt = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
                end_date_fmt = datetime.now().strftime("%Y%m%d")
                df = self.fetch_stock_em_gdzjc(start_date=start_date_fmt, end_date=end_date_fmt)
                
                # 再次查询
                df = self.pg_manager.query_df(sql)
            
            return df
        except Exception as e:
            print(f"获取近期股东增减持数据失败: {e}")
            return pd.DataFrame()
    
    def get_stock_holder_info(self, symbol):
        """获取股票的综合股东信息
        
        获取股票的股东户数、十大股东、十大流通股东、限售解禁、股东增减持等综合信息
        
        Args:
            symbol (str): 股票代码，如600000
            
        Returns:
            dict: 包含各类股东信息的字典
        """
        try:
            result = {}
            
            # 获取股东户数信息
            print(f"获取股票 {symbol} 的股东户数信息")
            gdhs_df = self.get_gdhs_by_code(symbol)
            if not gdhs_df.empty:
                result['股东户数'] = gdhs_df
            
            # 获取十大股东信息
            print(f"获取股票 {symbol} 的十大股东信息")
            if symbol.startswith('6'):
                symbol_fmt = f"sh{symbol}"
            else:
                symbol_fmt = f"sz{symbol}"
            sdgd_df = self.fetch_sdgd_top_10(symbol_fmt)
            if not sdgd_df.empty:
                result['十大股东'] = sdgd_df
            
            # 获取十大流通股东信息
            print(f"获取股票 {symbol} 的十大流通股东信息")
            sdltgd_df = self.fetch_sdltgd_top_10(symbol_fmt)
            if not sdltgd_df.empty:
                result['十大流通股东'] = sdltgd_df
            
            # 获取限售解禁信息
            print(f"获取股票 {symbol} 的限售解禁信息")
            xsjj_df = self.fetch_restricted_release_stockholder(symbol)
            if not xsjj_df.empty:
                result['限售解禁'] = xsjj_df
            
            # 获取股东增减持信息
            print(f"获取股票 {symbol} 的股东增减持信息")
            start_date = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")
            end_date = datetime.now().strftime("%Y%m%d")
            gdzjc_df = self.fetch_stock_em_gdzjc(symbol, start_date, end_date)
            if not gdzjc_df.empty:
                result['股东增减持'] = gdzjc_df
            
            # 获取高管持股信息
            print(f"获取股票 {symbol} 的高管持股信息")
            ggcg_df = self.fetch_stock_em_ggcg(symbol)
            if not ggcg_df.empty:
                result['高管持股'] = ggcg_df
            
            # 获取沪深港通持股信息
            print(f"获取股票 {symbol} 的沪深港通持股信息")
            hsgt_df = self.fetch_hsgt_individual(symbol)
            if not hsgt_df.empty:
                result['沪深港通持股'] = hsgt_df
            
            return result
        except Exception as e:
            print(f"获取股票 {symbol} 的综合股东信息失败: {e}")
            return {}
    
    def get_stockholder_statistics(self):
        """获取股东信息统计数据
        
        统计各类股东信息的数据量、更新时间等
        
        Returns:
            dict: 包含各类股东信息统计的字典
        """
        try:
            result = {}
            
            # 获取股东户数统计
            sql = "SELECT COUNT(*) as count, MAX(\"截止日期\") as last_date FROM \"股东户数\""
            gdhs_stat = self.pg_manager.query_df(sql)
            if not gdhs_stat.empty:
                result['股东户数'] = {
                    '数据量': int(gdhs_stat.iloc[0]['count']),
                    '最新日期': gdhs_stat.iloc[0]['last_date'].strftime("%Y-%m-%d") if pd.notna(gdhs_stat.iloc[0]['last_date']) else None
                }
            
            # 获取十大股东统计
            sql = "SELECT COUNT(*) as count, MAX(\"截止日期\") as last_date FROM \"十大股东\""
            sdgd_stat = self.pg_manager.query_df(sql)
            if not sdgd_stat.empty:
                result['十大股东'] = {
                    '数据量': int(sdgd_stat.iloc[0]['count']),
                    '最新日期': sdgd_stat.iloc[0]['last_date'].strftime("%Y-%m-%d") if pd.notna(sdgd_stat.iloc[0]['last_date']) else None
                }
            
            # 获取十大流通股东统计
            sql = "SELECT COUNT(*) as count, MAX(\"截止日期\") as last_date FROM \"十大流通股东\""
            sdltgd_stat = self.pg_manager.query_df(sql)
            if not sdltgd_stat.empty:
                result['十大流通股东'] = {
                    '数据量': int(sdltgd_stat.iloc[0]['count']),
                    '最新日期': sdltgd_stat.iloc[0]['last_date'].strftime("%Y-%m-%d") if pd.notna(sdltgd_stat.iloc[0]['last_date']) else None
                }
            
            # 获取限售解禁统计
            if self.pg_manager.table_exists("限售解禁批次"):
                sql = "SELECT COUNT(*) as count, MAX(\"解禁日期\") as last_date FROM \"限售解禁批次\""
                xsjj_stat = self.pg_manager.query_df(sql)
                if not xsjj_stat.empty:
                    result['限售解禁'] = {
                        '数据量': int(xsjj_stat.iloc[0]['count']),
                        '最新日期': xsjj_stat.iloc[0]['last_date'].strftime("%Y-%m-%d") if pd.notna(xsjj_stat.iloc[0]['last_date']) else None
                    }
            
            # 获取股东增减持统计
            if self.pg_manager.table_exists("股东增减持"):
                sql = "SELECT COUNT(*) as count, MAX(\"公告日期\") as last_date FROM \"股东增减持\""
                gdzjc_stat = self.pg_manager.query_df(sql)
                if not gdzjc_stat.empty:
                    result['股东增减持'] = {
                        '数据量': int(gdzjc_stat.iloc[0]['count']),
                        '最新日期': gdzjc_stat.iloc[0]['last_date'].strftime("%Y-%m-%d") if pd.notna(gdzjc_stat.iloc[0]['last_date']) else None
                    }
            
            # 获取高管持股统计
            if self.pg_manager.table_exists("高管持股"):
                sql = "SELECT COUNT(*) as count, MAX(\"变动日期\") as last_date FROM \"高管持股\""
                ggcg_stat = self.pg_manager.query_df(sql)
                if not ggcg_stat.empty:
                    result['高管持股'] = {
                        '数据量': int(ggcg_stat.iloc[0]['count']),
                        '最新日期': ggcg_stat.iloc[0]['last_date'].strftime("%Y-%m-%d") if pd.notna(ggcg_stat.iloc[0]['last_date']) else None
                    }
            
            # 获取Redis缓存更新时间
            update_times = {}
            for key in self.redis_manager.keys(f"{self.redis_update_time_key}:*"):
                module = key.split(':')[-1]
                value = self.redis_manager.get_value(key)
                if value:
                    update_times[module] = value
            
            result['更新时间'] = update_times
            
            return result
        except Exception as e:
            print(f"获取股东信息统计数据失败: {e}")
            return {}
    
    def get_gdhs_by_code(self, code, start_date=None, end_date=None):
        """根据股票代码获取股东户数数据
        
        Args:
            code (str): 股票代码，如000001
            start_date (str, optional): 开始日期，格式："2022-01-01"，默认为None
            end_date (str, optional): 结束日期，格式："2022-12-31"，默认为None
            
        Returns:
            pandas.DataFrame: 股东户数数据
        """
        try:
            # 构建SQL查询条件
            conditions = [f"\"股票代码\" = '{code}'"]
            params = []
            
            if start_date:
                conditions.append(f"\"截止日期\" >= %s")
                params.append(start_date)
            
            if end_date:
                conditions.append(f"\"截止日期\" <= %s")
                params.append(end_date)
            
            # 构建SQL查询
            sql = f"""
            SELECT * FROM \"股东户数\"  
            WHERE {' AND '.join(conditions)}
            ORDER BY \"截止日期\" DESC
            """
            
            # 执行查询
            df = self.pg_manager.query_df(sql, tuple(params) if params else None)
            
            if df.empty and not start_date and not end_date:
                # 如果数据库中没有数据，尝试从AKShare获取
                print(f"数据库中未找到股票 {code} 的股东户数数据，尝试从AKShare获取")
                df = self.fetch_gdhs_detail(symbol=code)
            
            return df
        except Exception as e:
            print(f"获取股票 {code} 的股东户数数据失败: {e}")
            return pd.DataFrame()
    
    def get_latest_gdhs(self, limit=100):
        """获取最新股东户数变化数据
        
        Args:
            limit (int, optional): 返回记录数量限制，默认为100
            
        Returns:
            pandas.DataFrame: 最新股东户数变化数据
        """
        try:
            # 构建SQL查询
            sql = f"""
            SELECT * FROM \"股东户数\"  
            ORDER BY \"截止日期\" DESC, \"较上期变化比例\" DESC
            LIMIT {limit}
            """
            
            # 执行查询
            df = self.pg_manager.query_df(sql)
            
            return df
        except Exception as e:
            print(f"获取最新股东户数变化数据失败: {e}")
            return pd.DataFrame()
    
    def fetch_sdgd_top_10(self, symbol, date=None):
        """获取个股十大股东数据
        
        Args:
            symbol (str): 股票代码，如sh600000或600000
            date (str, optional): 查询日期，格式："20210630"，默认为None，表示获取最新数据
            
        Returns:
            pandas.DataFrame: 十大股东数据
        """
        try:
            # 确保股票代码格式正确
            if symbol.isdigit():
                if symbol.startswith('6'):
                    symbol = f"sh{symbol}"
                else:
                    symbol = f"sz{symbol}"
            
            # 从Redis缓存获取数据
            cache_key = f"{self.redis_sdgd_prefix}{symbol}:{date if date else 'latest'}"
            cached_data = self.redis_manager.get_value(cache_key)
            
            if cached_data is not None:
                print(f"从缓存获取股票 {symbol} 的十大股东数据")
                return cached_data
            
            # 从AKShare获取数据
            print(f"从AKShare获取股票 {symbol} 的十大股东数据")
            df = ak.stock_gdfx_top_10_em(symbol=symbol, date=date)
            
            # 数据清洗和转换
            if not df.empty:
                # 缓存数据
                self.redis_manager.set_value(cache_key, df, expire=self.sdgd_expire)
                
                # 更新最后更新时间
                self.redis_manager.set_value(f"{self.redis_update_time_key}:十大股东", 
                                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                      expire=self.sdgd_expire)
                
                # 保存到PostgreSQL
                self._save_sdgd_to_postgresql(df, symbol)
            
            return df
        except Exception as e:
            print(f"获取股票 {symbol} 的十大股东数据失败: {e}")
            return pd.DataFrame()
    
    def _save_sdgd_to_postgresql(self, df, symbol):
        """将十大股东数据保存到PostgreSQL
        
        Args:
            df (pandas.DataFrame): 十大股东数据
            symbol (str): 股票代码
        """
        if df.empty:
            print("十大股东数据为空，跳过保存")
            return
        
        try:
            # 确保表存在
            if not self.pg_manager.table_exists("十大股东"):
                self.create_sdgd_table()
            
            # 处理数据
            processed_df = df.copy()
            
            # 提取股票代码和名称
            stock_code = symbol.replace("sh", "").replace("sz", "")
            stock_name = processed_df.iloc[0]['股票简称'] if '股票简称' in processed_df.columns else ""
            
            # 提取截止日期和公告日期
            end_date = None
            announce_date = None
            if '截止日期' in processed_df.columns:
                end_date = processed_df.iloc[0]['截止日期']
            if '公告日期' in processed_df.columns:
                announce_date = processed_df.iloc[0]['公告日期']
            
            # 准备数据框
            result_df = pd.DataFrame()
            result_df['股票代码'] = [stock_code] * len(processed_df)
            result_df['股票简称'] = [stock_name] * len(processed_df)
            result_df['截止日期'] = [end_date] * len(processed_df) if end_date else None
            result_df['公告日期'] = [announce_date] * len(processed_df) if announce_date else None
            result_df['股东名称'] = processed_df['股东名称']
            
            # 处理可能存在的列
            if '持股数量' in processed_df.columns:
                result_df['持股数量'] = processed_df['持股数量']
            if '持股比例' in processed_df.columns:
                result_df['持股比例'] = processed_df['持股比例']
            if '股本性质' in processed_df.columns:
                result_df['股本性质'] = processed_df['股本性质']
            if '股东性质' in processed_df.columns:
                result_df['股东类型'] = processed_df['股东性质']
            if '增减' in processed_df.columns:
                result_df['变动情况'] = processed_df['增减']
            
            # 保存数据
            conflict_columns = ["股票代码", "截止日期", "股东名称"]
            update_columns = [col for col in result_df.columns if col not in conflict_columns]
            
            self.pg_manager.insert_df("十大股东", result_df, conflict_columns, update_columns)
            print(f"成功保存{len(result_df)}条十大股东数据到PostgreSQL")
        except Exception as e:
            print(f"保存十大股东数据到PostgreSQL失败: {e}")
    
    def fetch_sdltgd_top_10(self, symbol, date=None):
        """获取个股十大流通股东数据
        
        Args:
            symbol (str): 股票代码，如sh600000或600000
            date (str, optional): 查询日期，格式："20210630"，默认为None，表示获取最新数据
            
        Returns:
            pandas.DataFrame: 十大流通股东数据
        """
        try:
            # 确保股票代码格式正确
            if symbol.isdigit():
                if symbol.startswith('6'):
                    symbol = f"sh{symbol}"
                else:
                    symbol = f"sz{symbol}"
            
            # 从Redis缓存获取数据
            cache_key = f"{self.redis_sdltgd_prefix}{symbol}:{date if date else 'latest'}"
            cached_data = self.redis_manager.get_value(cache_key)
            
            if cached_data is not None:
                print(f"从缓存获取股票 {symbol} 的十大流通股东数据")
                return cached_data
            
            # 从AKShare获取数据
            print(f"从AKShare获取股票 {symbol} 的十大流通股东数据")
            df = ak.stock_gdfx_free_top_10_em(symbol=symbol, date=date)
            
            # 数据清洗和转换
            if not df.empty:
                # 缓存数据
                self.redis_manager.set_value(cache_key, df, expire=self.sdltgd_expire)
                
                # 更新最后更新时间
                self.redis_manager.set_value(f"{self.redis_update_time_key}:十大流通股东", 
                                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                      expire=self.sdltgd_expire)
                
                # 保存到PostgreSQL
                self._save_sdltgd_to_postgresql(df, symbol)
            
            return df
        except Exception as e:
            print(f"获取股票 {symbol} 的十大流通股东数据失败: {e}")
            return pd.DataFrame()
    
    def _save_sdltgd_to_postgresql(self, df, symbol):
        """将十大流通股东数据保存到PostgreSQL
        
        Args:
            df (pandas.DataFrame): 十大流通股东数据
            symbol (str): 股票代码
        """
        if df.empty:
            print("十大流通股东数据为空，跳过保存")
            return
        
        try:
            # 确保表存在
            if not self.pg_manager.table_exists("十大流通股东"):
                self.create_sdltgd_table()
            
            # 处理数据
            processed_df = df.copy()
            
            # 提取股票代码和名称
            stock_code = symbol.replace("sh", "").replace("sz", "")
            stock_name = processed_df.iloc[0]['股票简称'] if '股票简称' in processed_df.columns else ""
            
            # 提取截止日期和公告日期
            end_date = None
            announce_date = None
            if '截止日期' in processed_df.columns:
                end_date = processed_df.iloc[0]['截止日期']
            if '公告日期' in processed_df.columns:
                announce_date = processed_df.iloc[0]['公告日期']
            
            # 准备数据框
            result_df = pd.DataFrame()
            result_df['股票代码'] = [stock_code] * len(processed_df)
            result_df['股票简称'] = [stock_name] * len(processed_df)
            result_df['截止日期'] = [end_date] * len(processed_df) if end_date else None
            result_df['公告日期'] = [announce_date] * len(processed_df) if announce_date else None
            result_df['股东名称'] = processed_df['股东名称']
            
            # 处理可能存在的列
            if '持股数量' in processed_df.columns:
                result_df['持股数量'] = processed_df['持股数量']
            if '持股比例' in processed_df.columns:
                result_df['持股比例'] = processed_df['持股比例']
            if '股东性质' in processed_df.columns:
                result_df['股东类型'] = processed_df['股东性质']
            if '增减' in processed_df.columns:
                result_df['变动情况'] = processed_df['增减']
            
            # 保存数据
            conflict_columns = ["股票代码", "截止日期", "股东名称"]
            update_columns = [col for col in result_df.columns if col not in conflict_columns]
            
            self.pg_manager.insert_df("十大流通股东", result_df, conflict_columns, update_columns)
            print(f"成功保存{len(result_df)}条十大流通股东数据到PostgreSQL")
        except Exception as e:
            print(f"保存十大流通股东数据到PostgreSQL失败: {e}")
    
    def create_jgcg_table(self):
        """创建机构持股表"""
        try:
            # 创建表SQL
            columns_dict = {
                "股票代码": "VARCHAR(10) NOT NULL",
                "股票简称": "VARCHAR(50) NOT NULL",
                "截止日期": "DATE NOT NULL",
                "机构名称": "TEXT NOT NULL",
                "持股数量": "FLOAT",
                "持股比例": "FLOAT",
                "持股市值": "FLOAT",
                "机构类型": "VARCHAR(50)",
                "增减情况": "VARCHAR(50)",
                "PRIMARY KEY": "(股票代码, 截止日期, 机构名称)"
            }
            
            # 创建表
            self.pg_manager.create_table("机构持股", columns_dict)
            
            # 创建索引
            self.pg_manager.create_index("机构持股", "idx_jgcg_code", ["股票代码"])
            self.pg_manager.create_index("机构持股", "idx_jgcg_date", ["截止日期"])
            self.pg_manager.create_index("机构持股", "idx_jgcg_name", ["机构名称"])
            
            return True
        except Exception as e:
            print(f"创建机构持股表失败: {e}")
            return False
    
    def fetch_institute_hold(self):
        """获取机构持股一览表数据
        
        Returns:
            pandas.DataFrame: 机构持股一览表数据
        """
        try:
            # 从Redis缓存获取数据
            cache_key = "机构持股:一览表"
            cached_data = self.redis_manager.get_value(cache_key)
            
            if cached_data is not None:
                print("从缓存获取机构持股一览表数据")
                return cached_data
            
            # 从AKShare获取数据
            print("从AKShare获取机构持股一览表数据")
            df = ak.stock_institute_hold()
            
            # 数据清洗和转换
            if not df.empty:
                # 缓存数据
                self.redis_manager.set_value(cache_key, df, expire=86400 * 7)  # 7天
                
                # 更新最后更新时间
                self.redis_manager.set_value("股东信息:更新时间:机构持股一览表", 
                                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                      expire=86400 * 7)
            
            return df
        except Exception as e:
            print(f"获取机构持股一览表数据失败: {e}")
            return pd.DataFrame()
    
    def fetch_institute_hold_detail(self, stock, quarter="20231"):
        """获取机构持股详情数据
        
        Args:
            stock (str): 股票代码，如600000
            quarter (str, optional): 季度，格式："20231"表示2023年第1季度，默认为"20231"
            
        Returns:
            pandas.DataFrame: 机构持股详情数据
        """
        try:
            # 从Redis缓存获取数据
            cache_key = f"机构持股:详情:{stock}:{quarter}"
            cached_data = self.redis_manager.get_value(cache_key)
            
            if cached_data is not None:
                print(f"从缓存获取股票 {stock} 的机构持股详情数据")
                return cached_data
            
            # 从AKShare获取数据
            print(f"从AKShare获取股票 {stock} 的机构持股详情数据")
            df = ak.stock_institute_hold_detail(stock=stock, quarter=quarter)
            
            # 数据清洗和转换
            if not df.empty:
                # 缓存数据
                self.redis_manager.set_value(cache_key, df, expire=86400 * 7)  # 7天
                
                # 更新最后更新时间
                self.redis_manager.set_value("股东信息:更新时间:机构持股详情", 
                                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                      expire=86400 * 7)
                
                # 保存到PostgreSQL
                self._save_jgcg_to_postgresql(df, stock, quarter)
            
            return df
        except Exception as e:
            print(f"获取股票 {stock} 的机构持股详情数据失败: {e}")
            return pd.DataFrame()
    
    def _save_jgcg_to_postgresql(self, df, stock, quarter):
        """将机构持股详情数据保存到PostgreSQL
        
        Args:
            df (pandas.DataFrame): 机构持股详情数据
            stock (str): 股票代码
            quarter (str): 季度
        """
        if df.empty:
            print("机构持股详情数据为空，跳过保存")
            return
        
        try:
            # 确保表存在
            if not self.pg_manager.table_exists("机构持股"):
                self.create_jgcg_table()
            
            # 处理数据
            processed_df = df.copy()
            
            # 提取股票代码和名称
            stock_code = stock
            stock_name = ""
            
            # 提取截止日期
            year = int(quarter[:4])
            q = int(quarter[4:])
            if q == 1:
                end_date = f"{year}-03-31"
            elif q == 2:
                end_date = f"{year}-06-30"
            elif q == 3:
                end_date = f"{year}-09-30"
            else:
                end_date = f"{year}-12-31"
            
            # 准备数据框
            result_df = pd.DataFrame()
            result_df['股票代码'] = [stock_code] * len(processed_df)
            result_df['股票简称'] = [stock_name] * len(processed_df)
            result_df['截止日期'] = [end_date] * len(processed_df)
            
            # 处理列名映射
            column_mapping = {
                '机构名称': '机构名称',
                '持股数量': '持股数量',
                '占流通股比': '持股比例',
                '持股市值': '持股市值',
                '机构类型': '机构类型',
                '变动状态': '增减情况'
            }
            
            # 映射列名
            for src, dst in column_mapping.items():
                if src in processed_df.columns:
                    result_df[dst] = processed_df[src]
            
            # 保存数据
            conflict_columns = ["股票代码", "截止日期", "机构名称"]
            update_columns = [col for col in result_df.columns if col not in conflict_columns]
            
            self.pg_manager.insert_df("机构持股", result_df, conflict_columns, update_columns)
            print(f"成功保存{len(result_df)}条机构持股详情数据到PostgreSQL")
        except Exception as e:
            print(f"保存机构持股详情数据到PostgreSQL失败: {e}")
    
    def get_jgcg_by_code(self, code, start_date=None, end_date=None):
        """根据股票代码获取机构持股数据
        
        Args:
            code (str): 股票代码，如600000
            start_date (str, optional): 开始日期，格式："2022-01-01"，默认为None
            end_date (str, optional): 结束日期，格式："2022-12-31"，默认为None
            
        Returns:
            pandas.DataFrame: 机构持股数据
        """
        try:
            # 构建SQL查询条件
            conditions = [f"\"股票代码\" = '{code}'"]
            params = []
            
            if start_date:
                conditions.append(f"\"截止日期\" >= %s")
                params.append(start_date)
            
            if end_date:
                conditions.append(f"\"截止日期\" <= %s")
                params.append(end_date)
            
            # 构建SQL查询
            sql = f"""
            SELECT * FROM \"机构持股\"  
            WHERE {' AND '.join(conditions)}
            ORDER BY \"截止日期\" DESC
            """
            
            # 执行查询
            df = self.pg_manager.query_df(sql, tuple(params) if params else None)
            
            if df.empty and not start_date and not end_date:
                # 如果数据库中没有数据，尝试从AKShare获取
                print(f"数据库中未找到股票 {code} 的机构持股数据，尝试从AKShare获取")
                # 获取当前年份和季度
                now = datetime.now()
                year = now.year
                quarter = (now.month - 1) // 3 + 1
                if now.month <= 3:  # 如果是第一季度，使用上一年第四季度的数据
                    year -= 1
                    quarter = 4
                quarter_str = f"{year}{quarter}"
                df = self.fetch_institute_hold_detail(stock=code, quarter=quarter_str)
            
            return df
        except Exception as e:
            print(f"获取股票 {code} 的机构持股数据失败: {e}")
            return pd.DataFrame()


# 测试代码
if __name__ == "__main__":
    # 初始化股东信息数据获取类
    stockholder = StockholderData()
    
    # 创建数据表（不输出创建成功信息）
    stockholder.create_gdhs_table()
    stockholder.create_sdgd_table()
    stockholder.create_sdltgd_table()
    stockholder.create_gdzjc_table()
    stockholder.create_ggcg_table()
    
    # 获取股东户数详情数据
    gdhs_df = stockholder.fetch_gdhs_detail(symbol="002164")
    if not gdhs_df.empty:
        print(f"股东户数详情数据：\n{gdhs_df.head()}")
    
    # 获取十大流通股东持股分析数据
    sdltgd_df = stockholder.fetch_sdltgd_holding_analyse(date="20250331")
    if not sdltgd_df.empty:
        print(f"十大流通股东持股分析数据：\n{sdltgd_df.head()}")
    
    # 获取沪深港通个股持股数据
    hsgt_df = stockholder.fetch_hsgt_individual(stock="002031")
    if not hsgt_df.empty:
        print(f"沪深港通个股持股数据：\n{hsgt_df.head()}")
    
    # 测试股东增减持接口
    try:
        gdzjc_df = stockholder.fetch_stock_em_gdzjc(symbol="001308", name="孙建华")
        if not gdzjc_df.empty:
            print(f"股东增减持数据：\n{gdzjc_df.head()}")
    except Exception as e:
        print(f"测试股东增减持接口失败: {e}")
    
    # 测试高管持股接口
    try:
        ggcg_df = stockholder.fetch_stock_em_ggcg()
        if not ggcg_df.empty:
            print(f"高管持股数据：\n{ggcg_df.head()}")
    except Exception as e:
        print(f"测试高管持股接口失败: {e}")