#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
指数行情数据获取模块

获取主要指数的历史行情数据，包括上证指数、深成指数、创业板指、科创综指、北证50、中证全指、沪深300、中证500、中证1000等
"""

import os
import sys
import time
import datetime
import pandas as pd
import akshare as ak
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent.parent)  # fetcher/index/index_quote.py -> stock-a
if project_root not in sys.path:
    sys.path.append(project_root)

from db.postgresql_manager import PostgreSQLManager
from db.redis_manager import RedisManager
from utils.config_loader import load_connection_config


class IndexQuoteManager:
    """指数行情数据管理类
    
    负责获取、更新和查询指数历史行情数据，支持增量更新和缓存机制
    """
    
    def __init__(self):
        """初始化指数行情数据管理器"""
        # 数据库连接
        self.pg_manager = PostgreSQLManager()
        self.redis_manager = RedisManager()
        
        # 加载配置
        self.config = load_connection_config()
        
        # 并行处理配置
        self.max_workers = 8  # 并行获取数据的最大线程数
        self.retry_count = 3  # 数据获取失败重试次数
        self.retry_delay = 2  # 重试间隔（秒）
        
        # 缓存配置
        self.cache_prefix = "index_quote:"  # Redis缓存前缀
        self.cache_expire = 3600  # 缓存过期时间（秒）
        
        # 指数信息配置
        self._init_index_info()
    
    def _init_index_info(self):
        """初始化指数信息"""
        # 指数上市日期字典
        self.index_start_dates = {
            "000001": "19901219",  # 上证指数
            "399001": "19910403",  # 深成指数
            "399006": "20100601",  # 创业板指
            "000688": "20190506",  # 科创综指
            "899050": "20221121",  # 北证50
            "000985": "20080121",  # 中证全指
            "000300": "20050408",  # 沪深300
            "000905": "20070115",  # 中证500
            "000852": "20141017"   # 中证1000
        }
        
        # 指数列表，格式为：(指数代码, 指数名称)
        self.index_list = [
            ("000001", "上证指数"),
            ("399001", "深成指数"),
            ("399006", "创业板指"),
            ("000688", "科创综指"),
            ("899050", "北证50"),
            ("000985", "中证全指"),
            ("000300", "沪深300"),
            ("000905", "中证500"),
            ("000852", "中证1000")
        ]
    
    def ensure_table_exists(self):
        """确保指数行情数据表存在
        
        Returns:
            bool: 表是否存在或创建成功
        """
        try:
            # 创建指数行情数据表
            sql_create_table = """
            CREATE TABLE IF NOT EXISTS "指数历史行情" (
                "指数代码" VARCHAR(10) NOT NULL,
                "指数名称" VARCHAR(50) NOT NULL,
                "日期" DATE NOT NULL,
                "开盘" FLOAT NOT NULL,
                "收盘" FLOAT NOT NULL,
                "最高" FLOAT NOT NULL,
                "最低" FLOAT NOT NULL,
                "成交量" numeric(38,0) NOT NULL,
                "成交额" numeric(38,0) NOT NULL,
                "振幅" FLOAT,
                "涨跌幅" FLOAT,
                "涨跌额" FLOAT,
                "换手率" FLOAT,
                PRIMARY KEY ("指数代码", "日期")
            );
            """
            
            # 创建日期索引
            sql_create_index = """
            CREATE INDEX IF NOT EXISTS "idx_指数历史行情_日期" ON "指数历史行情" ("日期");
            """
            
            # 执行SQL
            self.pg_manager.execute(sql_create_table)
            self.pg_manager.execute(sql_create_index)
            
            return True
        except Exception as e:
            print(f"确保指数行情数据表存在失败: {e}")
            return False
    
    def _get_cache_key(self, index_code, date_str=None):
        """生成缓存键
        
        Args:
            index_code (str): 指数代码
            date_str (str, optional): 日期字符串，格式为YYYYMMDD
            
        Returns:
            str: 缓存键
        """
        if date_str:
            return f"{self.cache_prefix}{index_code}:{date_str}"
        return f"{self.cache_prefix}{index_code}:last_date"
    
    def get_last_trade_date(self, index_code):
        """获取指数最后交易日期
        
        Args:
            index_code (str): 指数代码
            
        Returns:
            str: 最后交易日期，格式为YYYYMMDD
        """
        # 尝试从缓存获取
        cache_key = self._get_cache_key(index_code)
        cached_date = self.redis_manager.get_value(cache_key)
        
        if cached_date:
            # 确保缓存的日期是字符串类型
            if isinstance(cached_date, bytes):
                cached_date = cached_date.decode('utf-8')
            return cached_date
        
        try:
            # 查询数据库中该指数的最后交易日期
            sql = "SELECT MAX(\"日期\") FROM \"指数历史行情\" WHERE \"指数代码\" = %s;"
            result = self.pg_manager.query(sql, (index_code,))
            
            if result and result[0][0]:
                # 将日期转换为YYYYMMDD格式字符串
                last_date = result[0][0]
                date_str = last_date.strftime("%Y%m%d")
                
                # 缓存结果
                self.redis_manager.set_value(cache_key, date_str, expire=self.cache_expire)
                
                return date_str
            else:
                # 如果查询结果为空，返回指数特定上市日期
                start_date = self.index_start_dates.get(index_code, "20050104")
                return start_date
        except Exception as e:
            # 发生错误时返回指数特定上市日期
            start_date = self.index_start_dates.get(index_code, "20050104")
            return start_date
    
    def _is_update_needed(self, index_code, index_name):
        """检查指数是否需要更新
        
        Args:
            index_code (str): 指数代码
            index_name (str): 指数名称
            
        Returns:
            tuple: (是否需要更新, 开始日期, 结束日期)
        """
        # 获取最后交易日期
        last_date_str = self.get_last_trade_date(index_code)
        
        # 将字符串日期转换为datetime对象
        try:
            last_date = datetime.datetime.strptime(last_date_str, "%Y%m%d")
        except ValueError:
            print(f"指数 {index_name}({index_code}) 最后交易日期格式错误: {last_date_str}")
            return False, None, None
        
        # 获取当前日期
        current_date = datetime.datetime.now()
        
        # 检查是否是首次获取数据
        is_first_fetch = last_date_str == self.index_start_dates.get(index_code, "20050104")
        
        # 如果是首次获取，直接返回需要更新
        if is_first_fetch:
            return True, last_date_str, current_date.strftime("%Y%m%d")
        
        # 计算日期差
        date_diff = (current_date.date() - last_date.date()).days
        
        # 检查是否需要更新
        # 1. 周末情况处理
        if current_date.weekday() in [5, 6]:  # 周六或周日
            # 如果最后交易日是周五且日期差小于等于3天，则无需更新
            if last_date.weekday() == 4 and date_diff <= 3:
                return False, None, None
        
        # 2. 周一情况处理
        elif current_date.weekday() == 0:  # 周一
            # 如果最后交易日是上周五且日期差小于等于3天，则无需更新
            if last_date.weekday() == 4 and date_diff <= 3:
                return False, None, None
        
        # 3. 当天数据处理
        if last_date.date() == current_date.date():
            return False, None, None
        
        # 4. 设置起始日期为最后交易日的下一天
        start_date = last_date + datetime.timedelta(days=1)
        start_date_str = start_date.strftime("%Y%m%d")
        end_date_str = current_date.strftime("%Y%m%d")
        
        # 5. 检查起始日期是否晚于结束日期
        if start_date_str > end_date_str:
            return False, None, None
        
        # 6. 检查起始日期是否是当天
        if start_date_str == end_date_str:
            # 如果当天是交易日且已经收盘，则需要更新
            if current_date.weekday() < 5 and current_date.hour >= 15:
                return True, start_date_str, end_date_str
            return False, None, None
        
        return True, start_date_str, end_date_str
    
    def fetch_index_data(self, index_code, index_name, start_date, end_date, period="daily"):
        """获取指数历史行情数据
        
        Args:
            index_code (str): 指数代码
            index_name (str): 指数名称
            start_date (str): 开始日期，格式为YYYYMMDD
            end_date (str): 结束日期，格式为YYYYMMDD
            period (str, optional): 数据周期，可选值为daily, weekly, monthly
            
        Returns:
            pandas.DataFrame: 指数历史行情数据
        """
        # 检查参数
        if not all([index_code, index_name, start_date, end_date]):
            print(f"获取指数 {index_name}({index_code}) 数据参数不完整")
            return pd.DataFrame()
        
        print(f"获取指数 {index_name}({index_code}) 从 {start_date} 到 {end_date} 的历史行情数据...")
        
        # 重试机制
        for attempt in range(self.retry_count):
            try:
                # 使用akshare获取指数历史行情数据
                df = ak.index_zh_a_hist(symbol=index_code, period=period, start_date=start_date, end_date=end_date)
                
                # 如果数据为空，返回空DataFrame
                if df.empty:
                    print(f"指数 {index_name}({index_code}) 在指定日期范围内没有数据")
                    return pd.DataFrame()
                
                # 添加指数代码和名称列
                df['指数代码'] = index_code
                df['指数名称'] = index_name
                
                # 确保列名符合预期
                expected_columns = ['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']
                for col in expected_columns:
                    if col not in df.columns:
                        print(f"指数 {index_name}({index_code}) 数据缺少列: {col}")
                        return pd.DataFrame()
                
                # 调整列顺序
                df = df[['指数代码', '指数名称', '日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']]
                
                # 将日期列转换为datetime类型
                df['日期'] = pd.to_datetime(df['日期'])
                
                print(f"指数 {index_name}({index_code}) 获取到 {len(df)} 条数据")
                return df
            
            except Exception as e:
                # 网络错误或其他错误，进行重试
                print(f"获取指数 {index_name}({index_code}) 数据失败 (尝试 {attempt+1}/{self.retry_count}): {e}")
                
                # 最后一次尝试失败
                if attempt == self.retry_count - 1:
                    print(f"获取指数 {index_name}({index_code}) 数据失败，已达到最大重试次数")
                    return pd.DataFrame()
                
                # 延迟后重试
                time.sleep(self.retry_delay)
        
        return pd.DataFrame()
    
    def save_index_data(self, df):
        """保存指数历史行情数据到数据库
        
        Args:
            df (pandas.DataFrame): 指数历史行情数据
            
        Returns:
            bool: 保存是否成功
        """
        if df.empty:
            return False
        
        try:
            # 定义冲突时需要更新的列
            conflict_columns = ["指数代码", "日期"]
            update_columns = ["指数名称", "开盘", "收盘", "最高", "最低", "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率"]
            
            # 批量插入数据
            result = self.pg_manager.insert_df(
                table_name="指数历史行情",
                df=df,
                conflict_columns=conflict_columns,
                update_columns=update_columns
            )
            
            if result:
                # 更新缓存
                self._update_cache_after_save(df)
                print(f"成功保存 {len(df)} 条指数历史行情数据")
            
            return result
        except Exception as e:
            print(f"保存指数历史行情数据失败: {e}")
            return False
    
    def _update_cache_after_save(self, df):
        """保存数据后更新缓存
        
        Args:
            df (pandas.DataFrame): 保存的数据
        """
        try:
            # 按指数代码分组
            grouped = df.groupby('指数代码')
            
            for index_code, group in grouped:
                # 获取该指数的最新日期
                latest_date = group['日期'].max()
                date_str = latest_date.strftime("%Y%m%d")
                
                # 更新缓存
                cache_key = self._get_cache_key(index_code)
                self.redis_manager.set_value(cache_key, date_str, expire=self.cache_expire)
        except Exception as e:
            print(f"更新缓存失败: {e}")
    
    def update_single_index(self, index_code, index_name, period="daily"):
        """更新单个指数的历史行情数据
        
        Args:
            index_code (str): 指数代码
            index_name (str): 指数名称
            period (str, optional): 数据周期，可选值为daily, weekly, monthly
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # 检查是否需要更新
            need_update, start_date, end_date = self._is_update_needed(index_code, index_name)
            
            if not need_update:
                print(f"指数 {index_name}({index_code}) 数据已是最新，无需更新")
                return True
            
            # 获取数据
            df = self.fetch_index_data(index_code, index_name, start_date, end_date, period)
            
            # 保存数据
            if not df.empty:
                return self.save_index_data(df)
            
            return True  # 如果没有新数据，也视为成功
        except Exception as e:
            print(f"更新指数 {index_name}({index_code}) 数据失败: {e}")
            return False
    
    def update_all_indices(self, period="daily"):
        """更新所有指数的历史行情数据
        
        Args:
            period (str, optional): 数据周期，可选值为daily, weekly, monthly
            
        Returns:
            bool: 更新是否成功
        """
        # 确保数据表存在
        if not self.ensure_table_exists():
            return False
        
        # 统计成功更新的指数数量
        success_count = 0
        total_count = len(self.index_list)
        
        # 当前日期和星期
        current_date = datetime.datetime.now()
        current_weekday = current_date.weekday()
        
        # 如果当前是周末，所有指数都应该是最新的
        if current_weekday in [5, 6]:  # 周六、周日
            print("当前是周末，所有指数数据应该已是最新")
            for code, name in self.index_list:
                print(f"指数 {name}({code}) 数据已是最新（周末无交易），无需更新")
                success_count += 1
            return True
        
        # 使用线程池并行更新指数数据
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_index = {}
            for code, name in self.index_list:
                future = executor.submit(self.update_single_index, code, name, period)
                future_to_index[future] = (code, name)
            
            # 处理结果
            for future in as_completed(future_to_index):
                code, name = future_to_index[future]
                try:
                    if future.result():
                        success_count += 1
                except Exception as e:
                    print(f"更新指数 {name}({code}) 数据时发生异常: {e}")
        
        print(f"成功更新 {success_count}/{total_count} 个指数的历史行情数据")
        return success_count > 0
    
    def query_index_data(self, index_code=None, start_date=None, end_date=None):
        """查询指数历史行情数据
        
        Args:
            index_code (str, optional): 指数代码，如果为None则查询所有指数
            start_date (str, optional): 开始日期，格式为YYYYMMDD
            end_date (str, optional): 结束日期，格式为YYYYMMDD
            
        Returns:
            pandas.DataFrame: 指数历史行情数据
        """
        try:
            # 构建查询条件
            conditions = []
            params = []
            
            if index_code:
                conditions.append("\"指数代码\" = %s")
                params.append(index_code)
            
            if start_date:
                conditions.append("\"日期\" >= %s")
                params.append(pd.to_datetime(start_date))
            
            if end_date:
                conditions.append("\"日期\" <= %s")
                params.append(pd.to_datetime(end_date))
            
            # 构建查询SQL
            sql = "SELECT * FROM \"指数历史行情\""  
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            
            sql += " ORDER BY \"指数代码\", \"日期\""  
            
            # 执行查询
            df = self.pg_manager.query_df(sql, tuple(params) if params else None)
            
            return df
        except Exception as e:
            print(f"查询指数历史行情数据失败: {e}")
            return pd.DataFrame()
    
    def get_latest_index_data(self, index_code):
        """获取指数最新行情数据
        
        Args:
            index_code (str): 指数代码
            
        Returns:
            dict: 指数最新行情数据
        """
        try:
            # 查询最新数据
            sql = """
            SELECT * FROM "指数历史行情" 
            WHERE "指数代码" = %s 
            ORDER BY "日期" DESC 
            LIMIT 1
            """
            
            df = self.pg_manager.query_df(sql, (index_code,))
            
            if df.empty:
                return {}
            
            # 转换为字典
            latest_data = df.iloc[0].to_dict()
            
            return latest_data
        except Exception as e:
            print(f"获取指数 {index_code} 最新行情数据失败: {e}")
            return {}


# 测试代码
if __name__ == "__main__":
    # 创建指数行情数据管理器
    index_manager = IndexQuoteManager()
    
    # 更新所有指数的历史行情数据
    index_manager.update_all_indices()
    
    # 查询上证指数的历史行情数据
    #df = index_manager.query_index_data(index_code="000001", start_date="20230101")
    #print(df.head())