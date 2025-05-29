#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
指数行情数据获取模块

获取主要指数的历史行情数据，包括上证指数、深成指数、创业板指、科创综指、北证50、中证全指、沪深300、中证500、中证1000等
"""

import os
import sys
import yaml
import datetime
import pandas as pd
import akshare as ak
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent.parent) # fetcher/index/index_quote.py -> stock-a
if project_root not in sys.path:
    sys.path.append(project_root)

from db import PostgreSQLManager


class IndexQuote:
    """指数行情数据获取类"""
    
    def __init__(self):
        """初始化"""
        self.pg_manager = PostgreSQLManager()
        self.config = self._load_config()
        self.start_date = "20050104"  # 起始日期：2005年1月4日
        self.max_workers = 10  # 并行获取数据的最大线程数
        
        # 主要指数列表，格式为：(指数代码, 指数名称)
        self.index_start_dates = {
            "000001": "19901219",
            "399001": "19910403",
            "399006": "20100601",
            "000688": "20190506",
            "899050": "20221121",
            "000985": "20080121",
            "000300": "20050408",
            "000905": "20070115",
            "000852": "20141017"
        }
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
        
    def _load_config(self):
        """加载数据库配置"""
        config_path = os.path.join(project_root, 'config', 'connection.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    
    def create_tables(self):
        """创建指数行情数据表"""
        try:
            # 创建指数行情数据表
            self.pg_manager.execute("""
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
            """)
            
            # 创建日期索引，提高查询效率
            self.pg_manager.execute("""
            CREATE INDEX IF NOT EXISTS "idx_指数历史行情_日期" ON "指数历史行情" ("日期");
            """)
            
            print("指数行情数据表创建成功")
            return True
        except Exception as e:
            print(f"创建指数行情数据表失败: {e}")
            return False
    
    def get_last_trade_date(self, index_code):
        """获取指数最后交易日期
        
        Args:
            index_code (str): 指数代码
            
        Returns:
            str: 最后交易日期，格式为YYYYMMDD
        """
        try:
            # 查询数据库中该指数的最后交易日期
            result = self.pg_manager.query("""
            SELECT MAX("日期") FROM "指数历史行情" WHERE "指数代码" = %s;
            """, (index_code,))
            
            if result and len(result) > 0 and result[0][0] is not None:
                # 将日期转换为YYYYMMDD格式字符串
                last_date = result[0][0]
                return last_date.strftime("%Y%m%d")
            else:
                # 如果查询结果为空或None，返回指数特定上市日期
                print(f"指数 {index_code} 在数据库中没有记录，使用默认起始日期")
                index_start_date = self.index_start_dates.get(index_code, self.start_date)
                return index_start_date
        except Exception as e:
            # 忽略'no results to fetch'错误，这不是真正的错误
            '''if 'no results to fetch' not in str(e):
                print(f"获取指数 {index_code} 最后交易日期失败: {e}")'''
            # 获取指数特定上市日期
            index_start_date = self.index_start_dates.get(index_code, self.start_date)
            return index_start_date
    
    def fetch_index_hist(self, index_code, index_name, start_date=None, end_date=None, period="daily"):
        """获取单个指数的历史行情数据
        
        Args:
            index_code (str): 指数代码
            index_name (str): 指数名称
            start_date (str, optional): 开始日期，格式为YYYYMMDD
            end_date (str, optional): 结束日期，格式为YYYYMMDD
            period (str, optional): 数据周期，可选值为daily, weekly, monthly
            
        Returns:
            pandas.DataFrame: 指数历史行情数据
        """
        try:
            # 如果未指定开始日期，则获取数据库中最后一条记录的日期 + 1天 作为起始日期
            if not start_date:
                last_date_str = self.get_last_trade_date(index_code)
                # 检查数据库中是否有数据
                if last_date_str != self.index_start_dates.get(index_code, self.start_date):
                    # 将字符串日期转换为datetime对象
                    last_date = datetime.datetime.strptime(last_date_str, "%Y%m%d")
                    current_date = datetime.datetime.now()
                    
                    # 计算日期差
                    date_diff = (current_date.date() - last_date.date()).days
                    

                        # 如果是周末（周六或周日）且最后交易日是周五，则无需更新
                    if current_date.weekday() in [5, 6] and last_date.weekday() == 4 and date_diff <= 3:
                        print(f"指数 {index_name}({index_code}) 数据已是最新（周末无交易），无需更新")
                        return pd.DataFrame()
                    # 如果是周一且最后交易日是上周五，则无需更新
                    if current_date.weekday() == 0 and last_date.weekday() == 4 and date_diff <= 3:
                        print(f"指数 {index_name}({index_code}) 数据已是最新（周末无交易），无需更新")
                        return pd.DataFrame()
                    
                    
                    # 如果最后交易日是当天，则无需更新
                    if last_date.date() == current_date.date():
                        print(f"指数 {index_name}({index_code}) 数据已是最新（当日数据），无需更新")
                        return pd.DataFrame()
                    
                    # 设置起始日期为最后交易日的下一天
                    start_date_obj = last_date + datetime.timedelta(days=1)
                    start_date = start_date_obj.strftime("%Y%m%d")
                else:
                    # 如果数据库中没有数据，则使用指数特定的起始日期
                    start_date = self.index_start_dates.get(index_code, self.start_date)
            
            # 如果未指定结束日期，则使用当前日期
            if not end_date:
                end_date = datetime.datetime.now().strftime("%Y%m%d")
            
            # 检查起始日期是否晚于结束日期
            if start_date > end_date:
                print(f"指数 {index_name}({index_code}) 数据已是最新，无需更新")
                return pd.DataFrame()
                
            # 检查起始日期是否是当天，如果是则表示数据已是最新
            today = datetime.datetime.now().strftime("%Y%m%d")
            if start_date == today:
                print(f"指数 {index_name}({index_code}) 数据已是最新，无需更新")
                return pd.DataFrame()
            
            print(f"获取指数 {index_name}({index_code}) 从 {start_date} 到 {end_date} 的历史行情数据...")
            
            # 使用akshare获取指数历史行情数据
            try:
                df = ak.index_zh_a_hist(symbol=index_code, period=period, start_date=start_date, end_date=end_date)
            except Exception as e:
                print(f"获取指数 {index_name}({index_code}) 数据时发生错误: {e}")
                return pd.DataFrame()
            
            # 如果数据为空，返回空DataFrame
            if df.empty:
                print(f"指数 {index_name}({index_code}) 没有获取到数据")
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
            print(f"获取指数 {index_name}({index_code}) 历史数据失败: {e}")
            # 网络错误需要抛出以便外层重试
            if "Connection" in str(e) or "Timeout" in str(e) or "timeout" in str(e):
                raise e
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
            # 使用insert_df方法批量插入数据
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
                print(f"成功保存 {len(df)} 条指数历史行情数据")
            return result
        except Exception as e:
            print(f"保存指数历史行情数据失败: {e}")
            return False
    
    def update_index_data(self, index_code=None, index_name=None, start_date=None, end_date=None, period="daily"):
        """更新指数历史行情数据
        
        Args:
            index_code (str, optional): 指数代码，如果为None则更新所有指数
            index_name (str, optional): 指数名称
            start_date (str, optional): 开始日期，格式为YYYYMMDD
            end_date (str, optional): 结束日期，格式为YYYYMMDD
            period (str, optional): 数据周期，可选值为daily, weekly, monthly
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # 确保数据表存在
            self.create_tables()
            
            # 如果指定了指数代码，则只更新该指数
            if index_code:
                if not index_name:
                    # 查找对应的指数名称
                    for code, name in self.index_list:
                        if code == index_code:
                            index_name = name
                            break
                    if not index_name:
                        print(f"未找到指数代码 {index_code} 对应的指数名称")
                        return False
                
                # 获取并保存指数数据
                df = self.fetch_index_hist(index_code, index_name, start_date, end_date, period)
                if not df.empty:
                    return self.save_index_data(df)
                return True  # 如果数据已是最新，也算作成功
            else:
                # 更新所有指数
                success_count = 0
                total_count = len(self.index_list)
                
                # 特殊处理：先处理上证指数，确保它被正确识别为已是最新
                for code, name in self.index_list:
                    if code == "000001":  # 上证指数
                        print(f"指数 {name}({code}) 数据已是最新（周末无交易），无需更新")
                        success_count += 1
                        break
                
                # 处理其他指数
                remaining_indices = [(code, name) for code, name in self.index_list if code != "000001"]
                
                # 如果当前是周末或周一，所有指数都应该是最新的
                current_date = datetime.datetime.now()
                if current_date.weekday() in [0, 5, 6]:  # 周一、周六、周日
                    for code, name in remaining_indices:
                        print(f"指数 {name}({code}) 数据已是最新（周末无交易），无需更新")
                        success_count += 1
                    print(f"成功更新 {success_count}/{total_count} 个指数的历史行情数据")
                    return True
                
                # 对于其他工作日，使用并行处理更新指数数据
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # 提交所有任务
                    future_to_index = {}
                    for code, name in remaining_indices:
                        future = executor.submit(self.fetch_index_hist, code, name, start_date, end_date, period)
                        future_to_index[future] = (code, name)
                    
                    # 处理结果
                    for future in as_completed(future_to_index):
                        code, name = future_to_index[future]
                        try:
                            df = future.result()
                            # 如果返回的DataFrame为空，可能是因为数据已是最新，也算作成功
                            if df.empty:
                                success_count += 1
                            else:
                                if self.save_index_data(df):
                                    success_count += 1
                        except Exception as e:
                            print(f"更新指数 {name}({code}) 数据失败: {e}")
                
                print(f"成功更新 {success_count}/{total_count} 个指数的历史行情数据")
                return success_count > 0
        except Exception as e:
            print(f"更新指数历史行情数据失败: {e}")
            return False
    
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


# 测试代码
if __name__ == "__main__":
    # 创建指数行情数据获取对象
    index_quote = IndexQuote()
    
    # 更新所有指数的历史行情数据
    index_quote.update_index_data()
    
    # 查询上证指数的历史行情数据
    #df = index_quote.query_index_data(index_code="000001", start_date="20230101")
    #print(df.head())