#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
机构持仓数据获取模块

获取A股市场机构持仓相关数据，包括沪深港通持股、机构调研等
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
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入数据存储模块
from db.postgresql_manager import PostgreSQLManager
from db.redis_manager import RedisManager

# 导入AKShare
import akshare as ak


class Institutional:
    """机构持仓数据获取类
    
    负责获取A股市场机构持仓相关数据，包括沪深港通持股、机构调研等，并存储到数据库
    """
    
    def __init__(self):
        """初始化机构持仓数据获取类"""
        self.pg_manager = PostgreSQLManager()
        self.redis_manager = RedisManager()
        
        # Redis键前缀
        self.redis_hsgt_prefix = "沪深港通持股:"
        self.redis_jgdy_prefix = "机构调研:"
        self.redis_update_time_key = "机构持仓:更新时间"
        
        # 数据过期时间（秒）
        self.hsgt_expire = 86400  # 24小时
        self.jgdy_expire = 86400 * 7  # 7天
    
    def create_hsgt_institution_table(self):
        """创建沪深港通机构持股统计表"""
        try:
            # 先检查表是否存在，如果存在则删除
            self.pg_manager.execute('DROP TABLE IF EXISTS "沪深港通机构持股统计"')
            
            # 创建表SQL
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS "沪深港通机构持股统计" (
                "持股日期" DATE NOT NULL,
                "机构名称" VARCHAR(100) NOT NULL,
                "持股只数" INTEGER,
                "持股市值" FLOAT,
                "持股市值变化1日" FLOAT,
                "持股市值变化5日" FLOAT,
                "持股市值变化10日" FLOAT,
                "北向资金类型" VARCHAR(20),
                "更新时间" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY ("持股日期", "机构名称")
            );
            """
            
            # 执行SQL创建表
            self.pg_manager.execute(create_table_sql)
            
            # 创建索引
            self.pg_manager.create_index("沪深港通机构持股统计", "idx_hsgt_institution_date", ["持股日期"])
            self.pg_manager.create_index("沪深港通机构持股统计", "idx_hsgt_institution_name", ["机构名称"])
            
            print("沪深港通机构持股统计表创建成功")
            return True
        except Exception as e:
            print(f"创建沪深港通机构持股统计表失败: {e}")
            return False
    
    def create_jgdy_detail_table(self):
        """创建机构调研明细表"""
        try:
            # 先检查表是否存在，如果存在则删除
            self.pg_manager.execute('DROP TABLE IF EXISTS "机构调研明细"')
            
            # 创建表SQL
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS "机构调研明细" (
                "序号" INTEGER,
                "代码" VARCHAR(10) NOT NULL,
                "名称" VARCHAR(50) NOT NULL,
                "最新价" FLOAT,
                "调研机构" TEXT,
                "调研方式" VARCHAR(50),
                "调研人员" TEXT,
                "接待人员" TEXT,
                "接待地点" TEXT,
                "调研日期" DATE NOT NULL,
                "公告日期" DATE,
                "更新时间" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY ("代码", "调研日期", "序号")
            );
            """
            
            # 执行SQL创建表
            self.pg_manager.execute(create_table_sql)
            
            # 创建索引
            self.pg_manager.create_index("机构调研明细", "idx_jgdy_detail_code", ["代码"])
            self.pg_manager.create_index("机构调研明细", "idx_jgdy_detail_date", ["调研日期"])
            
            print("机构调研明细表创建成功")
            return True
        except Exception as e:
            print(f"创建机构调研明细表失败: {e}")
            return False
    
    def fetch_hsgt_institution_statistics(self, market="北向持股", start_date=None, end_date=None):
        """获取沪深港通机构持股统计数据
        
        Args:
            market (str, optional): 市场类型，可选值："北向持股"，默认为"北向持股"
            start_date (str, optional): 开始日期，格式："20220101"，默认为None，表示获取最近一个交易日数据
            end_date (str, optional): 结束日期，格式："20220101"，默认为None，表示获取到最近一个交易日数据
            
        Returns:
            pandas.DataFrame: 沪深港通机构持股统计数据
        """
        try:
            # 获取当前日期并确保使用有效的历史日期范围
            current_date = datetime.now()
            
            # 如果未指定结束日期，设置为昨天（避免使用当天日期可能没有数据）
            if not end_date:
                # 使用昨天的日期作为结束日期
                end_date = (current_date - timedelta(days=1)).strftime("%Y%m%d")
            else:
                # 确保结束日期不超过昨天
                end_date_obj = datetime.strptime(end_date, "%Y%m%d")
                if end_date_obj > current_date:
                    end_date = (current_date - timedelta(days=1)).strftime("%Y%m%d")
                    print(f"结束日期超过当前日期，已调整为昨天: {end_date}")
            
            # 如果未指定开始日期，设置为结束日期前7天
            if not start_date:
                # 计算开始日期（结束日期前7天）
                end_date_obj = datetime.strptime(end_date, "%Y%m%d")
                start_date = (end_date_obj - timedelta(days=7)).strftime("%Y%m%d")
            else:
                # 确保开始日期不超过结束日期
                start_date_obj = datetime.strptime(start_date, "%Y%m%d")
                end_date_obj = datetime.strptime(end_date, "%Y%m%d")
                if start_date_obj > end_date_obj:
                    start_date = (end_date_obj - timedelta(days=7)).strftime("%Y%m%d")
                    print(f"开始日期超过结束日期，已调整为结束日期前7天: {start_date}")
            
            # 从Redis缓存获取数据
            cache_key = f"{self.redis_hsgt_prefix}{market}:{start_date}_{end_date}"
            cached_data = self.redis_manager.get_value(cache_key)
            
            if cached_data is not None:
                print(f"从缓存获取沪深港通机构持股统计数据: {market}, {start_date} - {end_date}")
                return cached_data
            
            # 从AKShare获取数据
            print(f"从AKShare获取沪深港通机构持股统计数据: {market}, {start_date} - {end_date}")
            df = ak.stock_hsgt_institution_statistics_em(market=market, start_date=start_date, end_date=end_date)
            
            # 检查返回结果是否为None
            if df is None:
                print(f"AKShare返回数据为None，可能是所选日期范围没有数据: {start_date} - {end_date}")
                return pd.DataFrame()  # 返回空DataFrame而不是None
            
            # 数据清洗和转换
            if not df.empty:
                # 重命名列（如果需要）
                # 数据类型转换
                for col in df.columns:
                    if '持股市值' in col or '市值' in col:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # 添加北向资金类型列
                df['北向资金类型'] = market
                
                # 缓存数据
                self.redis_manager.set_value(cache_key, df, expire=self.hsgt_expire)
                
                # 更新最后更新时间
                self.redis_manager.set_value(self.redis_update_time_key, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            return df
        except Exception as e:
            print(f"获取沪深港通机构持股统计数据失败: {e}")
            return pd.DataFrame()
    
    def fetch_jgdy_detail(self, date=None):
        """获取机构调研明细数据
        
        Args:
            date (str, optional): 查询日期，格式："20220101"，默认为None，表示获取最近一个交易日数据
            
        Returns:
            pandas.DataFrame: 机构调研明细数据
        """
        try:
            # 获取当前日期
            current_date = datetime.now()
            
            # 如果未指定日期，设置为昨天（避免使用当天日期可能没有数据）
            if not date:
                date = (current_date - timedelta(days=1)).strftime("%Y%m%d")
            else:
                # 确保查询日期不超过当前日期
                try:
                    date_obj = datetime.strptime(date, "%Y%m%d")
                    if date_obj > current_date:
                        date = (current_date - timedelta(days=1)).strftime("%Y%m%d")
                        print(f"查询日期超过当前日期，已调整为昨天: {date}")
                except ValueError as e:
                    print(f"日期格式错误: {e}，已调整为昨天")
                    date = (current_date - timedelta(days=1)).strftime("%Y%m%d")
            
            # 从Redis缓存获取数据
            cache_key = f"{self.redis_jgdy_prefix}明细:{date}"
            cached_data = self.redis_manager.get_value(cache_key)
            
            if cached_data is not None:
                print(f"从缓存获取机构调研明细数据: {date}")
                return cached_data
            
            # 从AKShare获取数据
            print(f"从AKShare获取机构调研明细数据: {date}")
            df = ak.stock_jgdy_detail_em(date=date)
            
            # 检查返回结果是否为None
            if df is None:
                print(f"AKShare返回数据为None，可能是所选日期没有数据: {date}")
                return pd.DataFrame()  # 返回空DataFrame而不是None
            
            # 数据清洗和转换
            if not df.empty:
                # 缓存数据
                self.redis_manager.set_value(cache_key, df, expire=self.jgdy_expire)
                
                # 更新最后更新时间
                self.redis_manager.set_value(self.redis_update_time_key, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            return df
        except Exception as e:
            print(f"获取机构调研明细数据失败: {e}")
            return pd.DataFrame()
    
    def save_hsgt_institution_statistics(self, df):
        """保存沪深港通机构持股统计数据到PostgreSQL
        
        Args:
            df (pandas.DataFrame): 沪深港通机构持股统计数据
            
        Returns:
            bool: 保存是否成功
        """
        if df.empty:
            print("沪深港通机构持股统计数据为空，无需保存")
            return False
        
        try:
            # 转换日期格式
            df['持股日期'] = pd.to_datetime(df['持股日期']).dt.strftime('%Y-%m-%d')
            
            # 保存到PostgreSQL
            # 设置冲突列和更新列
            conflict_columns = ["持股日期", "机构名称"]
            update_columns = [col for col in df.columns if col not in conflict_columns]
            result = self.pg_manager.insert_df("沪深港通机构持股统计", df, conflict_columns, update_columns)
            
            if result:
                print(f"成功保存{len(df)}条沪深港通机构持股统计数据")
            else:
                print("保存沪深港通机构持股统计数据失败")
            
            return result
        except Exception as e:
            print(f"保存沪深港通机构持股统计数据异常: {e}")
            return False
    
    def save_jgdy_detail(self, df):
        """保存机构调研明细数据到PostgreSQL
        
        Args:
            df (pandas.DataFrame): 机构调研明细数据
            
        Returns:
            bool: 保存是否成功
        """
        if df.empty:
            print("机构调研明细数据为空，无需保存")
            return False
        
        try:
            # 转换日期格式
            df['调研日期'] = pd.to_datetime(df['调研日期']).dt.strftime('%Y-%m-%d')
            df['公告日期'] = pd.to_datetime(df['公告日期']).dt.strftime('%Y-%m-%d')
            
            # 确保DataFrame只包含表中定义的列
            expected_columns = ["序号", "代码", "名称", "最新价", "调研机构", "调研方式", "调研人员", "接待人员", "接待地点", "调研日期", "公告日期"]
            df_filtered = df[[col for col in expected_columns if col in df.columns]]
            
            # 保存到PostgreSQL
            # 设置冲突列和更新列
            conflict_columns = ["代码", "调研日期", "序号"]
            update_columns = [col for col in df_filtered.columns if col not in conflict_columns]
            result = self.pg_manager.insert_df("机构调研明细", df_filtered, conflict_columns, update_columns)
            
            if result:
                print(f"成功保存{len(df)}条机构调研明细数据")
            else:
                print("保存机构调研明细数据失败")
            
            return result
        except Exception as e:
            print(f"保存机构调研明细数据异常: {e}")
            return False
    
    def update_hsgt_institution_statistics(self, days=7):
        """更新最近N天的沪深港通机构持股统计数据
        
        Args:
            days (int, optional): 更新天数，默认为7天
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # 计算日期范围（使用昨天作为结束日期，避免使用当天日期可能没有数据）
            current_date = datetime.now()
            end_date = (current_date - timedelta(days=1)).strftime("%Y%m%d")
            start_date = (current_date - timedelta(days=days+1)).strftime("%Y%m%d")
            
            print(f"更新沪深港通机构持股统计数据，日期范围: {start_date} - {end_date}")
            
            # 获取数据（使用改进后的fetch方法，它会处理日期验证和错误处理）
            df = self.fetch_hsgt_institution_statistics(market="北向持股", start_date=start_date, end_date=end_date)
            
            # 保存数据
            if not df.empty:
                return self.save_hsgt_institution_statistics(df)
            else:
                print("获取沪深港通机构持股统计数据为空，无需更新")
                return False
        except Exception as e:
            print(f"更新沪深港通机构持股统计数据异常: {e}")
            return False
    
    def update_jgdy_detail(self, days=7):
        """更新最近N天的机构调研明细数据
        
        Args:
            days (int, optional): 更新天数，默认为7天
            
        Returns:
            bool: 更新是否成功
        """
        try:
            success_count = 0
            current_date = datetime.now()
            
            print(f"开始更新最近{days}天的机构调研明细数据")
            
            # 逐日更新，从昨天开始往前推
            for i in range(days):
                # 使用昨天作为起始日期，避免使用当天日期可能没有数据
                date = (current_date - timedelta(days=i+1)).strftime("%Y%m%d")
                
                print(f"更新机构调研明细数据，日期: {date}")
                
                # 获取数据（使用改进后的fetch方法，它会处理日期验证和错误处理）
                df = self.fetch_jgdy_detail(date=date)
                
                # 保存数据
                if not df.empty:
                    if self.save_jgdy_detail(df):
                        success_count += 1
                else:
                    print(f"日期 {date} 没有机构调研明细数据")
                
                # 避免频繁请求
                time.sleep(1)
            
            print(f"成功更新{success_count}天的机构调研明细数据")
            return success_count > 0
        except Exception as e:
            print(f"更新机构调研明细数据异常: {e}")
            return False


# 测试代码
if __name__ == "__main__":
    # 创建机构持仓数据获取实例
    inst = Institutional()
    
    # 创建数据表
    inst.create_hsgt_institution_table()
    inst.create_jgdy_detail_table()
    
    # 更新数据
    inst.update_hsgt_institution_statistics(days=7)
    inst.update_jgdy_detail(days=3)