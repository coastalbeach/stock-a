#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
板块实时数据获取模块

获取行业板块和概念板块的实时数据，包括行业名称、代码、涨跌幅、成交量等信息
数据来源：东方财富网


建议：
- 如果只需要板块实时数据，可以使用BoardRealtime类
- 如果需要板块成分股等更多功能，建议使用SectorData类
"""

import os
import sys
import time
import pandas as pd
from pathlib import Path

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent.parent) # fetcher/market/board_realtime.py -> stock-a
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入数据存储模块
from db import PostgreSQLManager, RedisManager

# 导入akshare接口
import akshare as ak


class BoardRealtime:
    """板块实时数据获取类
    
    获取行业板块和概念板块的实时数据，并存储到PostgreSQL和Redis中
    """
    
    def __init__(self):
        """初始化数据库连接"""
        self.pg_manager = PostgreSQLManager()
        self.redis_manager = RedisManager()
        
        # 创建数据表
        self._create_tables()
    
    def _create_tables(self):
        """创建数据表"""
        # 创建行业板块表
        industry_table_sql = """
        CREATE TABLE IF NOT EXISTS 行业板块 (
            板块代码 VARCHAR(20) PRIMARY KEY,
            行业名称 VARCHAR(50) NOT NULL,
            最新价 NUMERIC(20, 2),
            涨跌额 NUMERIC(20, 2),
            涨跌幅 NUMERIC(10, 2),
            总市值 BIGINT,
            换手率 NUMERIC(10, 2),
            上涨家数 INTEGER,
            下跌家数 INTEGER,
            领涨股票 VARCHAR(20),
            领涨股票涨跌幅 NUMERIC(10, 2),
            更新时间 TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        self.pg_manager.execute(industry_table_sql)
        
        # 创建概念板块表
        concept_table_sql = """
        CREATE TABLE IF NOT EXISTS 概念板块 (
            板块代码 VARCHAR(20) PRIMARY KEY,
            板块名称 VARCHAR(50) NOT NULL,
            最新价 NUMERIC(20, 2),
            涨跌额 NUMERIC(20, 2),
            涨跌幅 NUMERIC(10, 2),
            总市值 BIGINT,
            换手率 NUMERIC(10, 2),
            上涨家数 INTEGER,
            下跌家数 INTEGER,
            领涨股票 VARCHAR(20),
            领涨股票涨跌幅 NUMERIC(10, 2),
            更新时间 TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        self.pg_manager.execute(concept_table_sql)
    
    def get_industry_board_data(self):
        """获取行业板块实时数据
        
        Returns:
            pandas.DataFrame: 行业板块实时数据
        """
        try:
            # 调用akshare接口获取行业板块数据
            df = ak.stock_board_industry_name_em()
            
            # 删除'排名'列，避免插入错误
            if '排名' in df.columns:
                df = df.drop(columns=['排名'])
            
            # 重命名列名
            df.rename(columns={
                '领涨股票-涨跌幅': '领涨股票涨跌幅'
            }, inplace=True)
            
            # 添加更新时间列
            df['更新时间'] = pd.Timestamp.now()
            
            return df
        except Exception as e:
            print(f"获取行业板块数据失败: {e}")
            return None
    
    def get_concept_board_data(self):
        """获取概念板块实时数据
        
        Returns:
            pandas.DataFrame: 概念板块实时数据
        """
        try:
            # 调用akshare接口获取概念板块数据
            df = ak.stock_board_concept_name_em()
            
            # 删除'排名'列，避免插入错误
            if '排名' in df.columns:
                df = df.drop(columns=['排名'])
            
            # 重命名列名
            df.rename(columns={
                '领涨股票-涨跌幅': '领涨股票涨跌幅'
            }, inplace=True)
            
            # 添加更新时间列
            df['更新时间'] = pd.Timestamp.now()
            
            return df
        except Exception as e:
            print(f"获取概念板块数据失败: {e}")
            return None
    
    def save_to_postgresql(self, data, table_name):
        """保存数据到PostgreSQL
        
        Args:
            data (pandas.DataFrame): 板块数据
            table_name (str): 表名
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 使用insert_df方法将DataFrame插入数据表
            # 设置冲突列为板块代码，更新除板块代码外的所有列
            conflict_columns = ['板块代码']
            update_columns = [col for col in data.columns if col != '板块代码']
            
            # 执行批量插入
            self.pg_manager.insert_df(table_name, data, conflict_columns, update_columns)
            
            print(f"成功保存{len(data)}条{table_name}数据到PostgreSQL")
            return True
        except Exception as e:
            print(f"保存{table_name}数据到PostgreSQL失败: {e}")
            return False
    
    def save_to_redis(self, data, key_prefix):
        """保存数据到Redis
        
        Args:
            data (pandas.DataFrame): 板块数据
            key_prefix (str): Redis键前缀
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 将DataFrame转换为字典列表
            data_dict = data.to_dict(orient='records')
            
            # 保存整个数据集到Redis
            self.redis_manager.set_value(f"{key_prefix}:all", data_dict, expire=3600)
            
            # 按板块代码分别保存
            for item in data_dict:
                board_code = item['板块代码']
                self.redis_manager.set_value(f"{key_prefix}:{board_code}", item, expire=3600)
            
            print(f"成功保存{len(data)}条{key_prefix}数据到Redis")
            return True
        except Exception as e:
            print(f"保存{key_prefix}数据到Redis失败: {e}")
            return False
    
    def update_industry_board(self):
        """更新行业板块数据"""
        # 获取行业板块数据
        industry_data = self.get_industry_board_data()
        if industry_data is not None:
            industry_data.rename(columns={
                '板块名称': '行业名称'
            }, inplace=True)
            # 保存到PostgreSQL
            self.save_to_postgresql(industry_data, '行业板块')
            # 保存到Redis
            self.save_to_redis(industry_data, 'industry_board')
    
    def update_concept_board(self):
        """更新概念板块数据"""
        # 获取概念板块数据
        concept_data = self.get_concept_board_data()
        if concept_data is not None:
            # 保存到PostgreSQL
            self.save_to_postgresql(concept_data, '概念板块')
            # 保存到Redis
            self.save_to_redis(concept_data, 'concept_board')
    
    def update_all(self):
        """更新所有板块数据"""
        self.update_industry_board()
        self.update_concept_board()
    
    def update_continuously(self, interval=60):
        """持续更新板块数据
        
        Args:
            interval (int): 更新间隔（秒）
        """
        print(f"开始持续更新板块数据，更新间隔：{interval}秒")
        try:
            while True:
                start_time = time.time()
                
                # 更新所有板块数据
                self.update_all()
                
                # 计算耗时和等待时间
                elapsed = time.time() - start_time
                wait_time = max(0, interval - elapsed)
                
                print(f"更新完成，耗时：{elapsed:.2f}秒，等待{wait_time:.2f}秒后进行下一次更新")
                time.sleep(wait_time)
        except KeyboardInterrupt:
            print("手动停止更新")
        except Exception as e:
            print(f"更新过程中发生错误: {e}")


# 测试代码
if __name__ == "__main__":
    board_realtime = BoardRealtime()
    
    # 更新一次
    board_realtime.update_all()
    
    # 持续更新（间隔60秒）
    # board_realtime.update_continuously(interval=60)