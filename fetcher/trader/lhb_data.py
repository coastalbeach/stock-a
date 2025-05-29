#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
龙虎榜数据获取模块

获取A股市场龙虎榜数据，包括龙虎榜详情、上榜原因、交易金额等信息
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
project_root = str(Path(__file__).resolve().parent.parent.parent) # fetcher/trader/lhb_data.py -> stock-a
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入数据存储模块
from db import PostgreSQLManager, RedisManager
from utils.config_loader import load_config

# 导入AKShare
import akshare as ak


class LhbData:
    """龙虎榜数据获取类
    
    负责获取A股市场龙虎榜相关数据，包括龙虎榜详情、上榜原因、交易金额等，并存储到数据库
    """
    
    def __init__(self):
        """初始化龙虎榜数据获取类"""
        self.pg_manager = PostgreSQLManager()
        self.redis_manager = RedisManager()
        
        # Redis键前缀
        self.redis_lhb_prefix = "龙虎榜:"
        
        # 创建数据表
        self._create_tables()
    
    def _create_tables(self):
        """创建龙虎榜相关数据表"""
        # 龙虎榜详情表
        create_lhb_detail_table_sql = """
        CREATE TABLE IF NOT EXISTS 龙虎榜详情 (
            代码 VARCHAR(10) NOT NULL,
            名称 VARCHAR(50),
            上榜日 DATE NOT NULL,
            解读 TEXT,
            收盘价 FLOAT,
            涨跌幅 FLOAT,
            龙虎榜净买额 FLOAT,
            龙虎榜买入额 FLOAT,
            龙虎榜卖出额 FLOAT,
            龙虎榜成交额 FLOAT,
            市场总成交额 BIGINT,
            净买额占总成交比 FLOAT,
            成交额占总成交比 FLOAT,
            换手率 FLOAT,
            流通市值 FLOAT,
            上榜原因 TEXT NOT NULL,
            上榜后1日 FLOAT,
            上榜后2日 FLOAT,
            上榜后5日 FLOAT,
            上榜后10日 FLOAT,
            PRIMARY KEY (代码, 上榜日, 上榜原因)
        );
        """
        self.pg_manager.execute(create_lhb_detail_table_sql)
        
        # 创建索引
        create_index_sql = """
        CREATE INDEX IF NOT EXISTS idx_lhb_detail_代码 ON 龙虎榜详情(代码);
        CREATE INDEX IF NOT EXISTS idx_lhb_detail_上榜日 ON 龙虎榜详情(上榜日);
        CREATE INDEX IF NOT EXISTS idx_lhb_detail_上榜原因 ON 龙虎榜详情(上榜原因);
        """
        self.pg_manager.execute(create_index_sql)
    
    def fetch_lhb_detail(self, start_date=20050104, end_date=None):
        """获取龙虎榜详情数据
        
        Args:
            start_date (str, optional): 开始日期，格式：YYYYMMDD，默认为当前日期前7天
            end_date (str, optional): 结束日期，格式：YYYYMMDD，默认为当前日期
            
        Returns:
            pandas.DataFrame: 龙虎榜详情数据
        """
        # 设置默认日期范围
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        try:
            # 调用AKShare接口获取龙虎榜详情数据
            print(f"正在获取从 {start_date} 到 {end_date} 的龙虎榜详情数据...")
            lhb_detail_df = ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)
            
            if lhb_detail_df.empty:
                print("未获取到龙虎榜详情数据")
                return pd.DataFrame()
            
            print(f"成功获取龙虎榜详情数据，共 {len(lhb_detail_df)} 条记录")
            return lhb_detail_df
        except Exception as e:
            print(f"获取龙虎榜详情数据失败: {e}")
            return pd.DataFrame()
    
    def process_lhb_detail(self, lhb_detail_df):
        """处理龙虎榜详情数据
        
        Args:
            lhb_detail_df (pandas.DataFrame): 龙虎榜详情数据
            
        Returns:
            pandas.DataFrame: 处理后的龙虎榜详情数据
        """
        if lhb_detail_df.empty:
            return pd.DataFrame()
        
        # 数据清洗和转换
        try:
            # 转换日期格式
            lhb_detail_df['上榜日'] = pd.to_datetime(lhb_detail_df['上榜日']).dt.date
            
            # 处理数值列，将百分比转换为小数
            percent_columns = ['涨跌幅', '净买额占总成交比', '成交额占总成交比', '换手率', '上榜后1日', '上榜后2日', '上榜后5日', '上榜后10日']
            for col in percent_columns:
                if col in lhb_detail_df.columns:
                    lhb_detail_df[col] = lhb_detail_df[col].astype(float) / 100
            
            # 处理NaN值
            lhb_detail_df = lhb_detail_df.fillna({
                '上榜后1日': 0,
                '上榜后2日': 0,
                '上榜后5日': 0,
                '上榜后10日': 0
            })
            
            return lhb_detail_df
        except Exception as e:
            print(f"处理龙虎榜详情数据失败: {e}")
            return pd.DataFrame()
    
    def save_to_postgresql(self, lhb_detail_df):
        """将龙虎榜详情数据保存到PostgreSQL数据库
        
        Args:
            lhb_detail_df (pandas.DataFrame): 处理后的龙虎榜详情数据
            
        Returns:
            bool: 保存是否成功
        """
        if lhb_detail_df.empty:
            return False
        
        try:
            # 构建插入SQL语句
            insert_sql = """
            INSERT INTO 龙虎榜详情 (
                代码, 名称, 上榜日, 解读, 收盘价, 涨跌幅, 
                龙虎榜净买额, 龙虎榜买入额, 龙虎榜卖出额, 龙虎榜成交额, 
                市场总成交额, 净买额占总成交比, 成交额占总成交比, 
                换手率, 流通市值, 上榜原因, 上榜后1日, 上榜后2日, 上榜后5日, 上榜后10日
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (代码, 上榜日, 上榜原因) 
            DO UPDATE SET 
                名称 = EXCLUDED.名称,
                解读 = EXCLUDED.解读,
                收盘价 = EXCLUDED.收盘价,
                涨跌幅 = EXCLUDED.涨跌幅,
                龙虎榜净买额 = EXCLUDED.龙虎榜净买额,
                龙虎榜买入额 = EXCLUDED.龙虎榜买入额,
                龙虎榜卖出额 = EXCLUDED.龙虎榜卖出额,
                龙虎榜成交额 = EXCLUDED.龙虎榜成交额,
                市场总成交额 = EXCLUDED.市场总成交额,
                净买额占总成交比 = EXCLUDED.净买额占总成交比,
                成交额占总成交比 = EXCLUDED.成交额占总成交比,
                换手率 = EXCLUDED.换手率,
                流通市值 = EXCLUDED.流通市值,
                上榜后1日 = EXCLUDED.上榜后1日,
                上榜后2日 = EXCLUDED.上榜后2日,
                上榜后5日 = EXCLUDED.上榜后5日,
                上榜后10日 = EXCLUDED.上榜后10日;
            """
            
            # 逐行插入数据
            for _, row in lhb_detail_df.iterrows():
                params = (
                    row.get('代码'),
                    row.get('名称'),
                    row.get('上榜日'),
                    row.get('解读'),
                    row.get('收盘价'),
                    row.get('涨跌幅'),
                    row.get('龙虎榜净买额'),
                    row.get('龙虎榜买入额'),
                    row.get('龙虎榜卖出额'),
                    row.get('龙虎榜成交额'),
                    row.get('市场总成交额'),
                    row.get('净买额占总成交比'),
                    row.get('成交额占总成交比'),
                    row.get('换手率'),
                    row.get('流通市值'),
                    row.get('上榜原因'),
                    row.get('上榜后1日'),
                    row.get('上榜后2日'),
                    row.get('上榜后5日'),
                    row.get('上榜后10日')
                )
                self.pg_manager.execute(insert_sql, params)
            
            print(f"成功保存 {len(lhb_detail_df)} 条龙虎榜详情数据到PostgreSQL数据库")
            return True
        except Exception as e:
            print(f"保存龙虎榜详情数据到PostgreSQL数据库失败: {e}")
            return False
    
    def save_to_redis(self, lhb_detail_df):
        """将龙虎榜详情数据保存到Redis缓存
        
        Args:
            lhb_detail_df (pandas.DataFrame): 处理后的龙虎榜详情数据
            
        Returns:
            bool: 保存是否成功
        """
        if lhb_detail_df.empty:
            return False
        
        try:
            # 获取最近的上榜日期
            latest_date = lhb_detail_df['上榜日'].max()
            latest_date_str = latest_date.strftime('%Y-%m-%d') if isinstance(latest_date, datetime) else str(latest_date)
            
            # 筛选最近日期的数据
            latest_df = lhb_detail_df[lhb_detail_df['上榜日'] == latest_date]
            
            # 按股票代码分组，将数据保存到Redis
            for code, group in latest_df.groupby('代码'):
                key = f"{self.redis_lhb_prefix}{code}:{latest_date_str}"
                # 将DataFrame转换为JSON字符串
                json_data = group.to_json(orient='records', force_ascii=False)
                # 设置Redis缓存，有效期为1天
                self.redis_manager.set_value(key, json_data, expire=86400)
            
            print(f"成功保存 {len(latest_df)} 条龙虎榜详情数据到Redis缓存")
            return True
        except Exception as e:
            print(f"保存龙虎榜详情数据到Redis缓存失败: {e}")
            return False
    
    def get_latest_lhb_date(self):
        """获取数据库中最新的龙虎榜数据日期
        
        Returns:
            str: 最新日期，格式：YYYYMMDD，如果没有数据则返回None
        """
        try:
            query_sql = """
            SELECT MAX(上榜日) FROM 龙虎榜详情
            """
            result = self.pg_manager.query(query_sql)
            if result and result[0][0]:
                # 将日期转换为YYYYMMDD格式字符串
                latest_date = result[0][0]
                if isinstance(latest_date, str):
                    # 如果是字符串格式，尝试转换为日期对象
                    latest_date = datetime.strptime(latest_date, '%Y-%m-%d').date()
                return latest_date.strftime('%Y%m%d')
            return None
        except Exception as e:
            print(f"获取最新龙虎榜数据日期失败: {e}")
            return None
            
    def get_tenth_recent_date(self):
        """获取数据库中第十个最近的龙虎榜数据日期（去重后）
        
        Returns:
            str: 第十个最近日期，格式：YYYYMMDD，如果没有足够数据则返回最早日期或None
        """
        try:
            # 查询去重后的上榜日期，按日期降序排列
            query_sql = """
            SELECT DISTINCT 上榜日 FROM 龙虎榜详情
            ORDER BY 上榜日 DESC
            """
            result = self.pg_manager.query(query_sql)
            
            # 如果没有数据，返回None
            if not result:
                return None
                
            # 如果数据少于10条，返回最后一条（最早的日期）
            if len(result) < 10:
                earliest_date = result[-1][0]
                if isinstance(earliest_date, str):
                    earliest_date = datetime.strptime(earliest_date, '%Y-%m-%d').date()
                return earliest_date.strftime('%Y%m%d')
            
            # 返回第十个日期
            tenth_date = result[9][0]  # 索引从0开始，所以第10个是索引9
            if isinstance(tenth_date, str):
                tenth_date = datetime.strptime(tenth_date, '%Y-%m-%d').date()
            return tenth_date.strftime('%Y%m%d')
        except Exception as e:
            print(f"获取第十个最近龙虎榜数据日期失败: {e}")
            return None
    
    def update_lhb_data(self, start_date=None, end_date=None):
        """更新龙虎榜数据
        
        Args:
            start_date (str, optional): 开始日期，格式：YYYYMMDD
            end_date (str, optional): 结束日期，格式：YYYYMMDD，默认为当前日期
            
        Returns:
            bool: 更新是否成功
        """
        # 设置默认结束日期为当前日期
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        # 如果未指定开始日期，则获取数据库中第十个最近日期
        if start_date is None:
            # 获取第十个最近日期作为起始日期
            tenth_recent_date = self.get_tenth_recent_date()
            if tenth_recent_date:
                start_date = tenth_recent_date
            else:
                # 如果数据库中没有足够数据，则获取最新日期
                latest_date = self.get_latest_lhb_date()
                if latest_date:
                    # 从最新日期前15天开始获取数据，确保能更新'上榜后10日'等列
                    start_date_obj = datetime.strptime(latest_date, '%Y%m%d').date() - timedelta(days=15)  # 考虑节假日，使用15天
                    start_date = start_date_obj.strftime('%Y%m%d')
                else:
                    # 如果数据库中没有数据，则使用默认起始日期
                    start_date = '20050104'  # 龙虎榜数据最早日期
        
        print(f"更新龙虎榜数据，时间范围: {start_date} 至 {end_date}")
        
        # 获取龙虎榜详情数据
        lhb_detail_df = self.fetch_lhb_detail(start_date, end_date)
        if lhb_detail_df.empty:
            return False
        
        # 处理数据
        processed_df = self.process_lhb_detail(lhb_detail_df)
        if processed_df.empty:
            return False
        
        # 保存到PostgreSQL数据库
        pg_result = self.save_to_postgresql(processed_df)
        
        # 保存到Redis缓存
        redis_result = self.save_to_redis(processed_df)
        
        return pg_result and redis_result
    
    def get_lhb_data_by_date(self, date):
        """根据日期获取龙虎榜数据
        
        Args:
            date (str): 日期，格式：YYYY-MM-DD
            
        Returns:
            pandas.DataFrame: 龙虎榜数据
        """
        try:
            query_sql = """
            SELECT * FROM 龙虎榜详情
            WHERE 上榜日 = %s
            ORDER BY 涨跌幅 DESC
            """
            result = self.pg_manager.query(query_sql, (date,))
            return pd.DataFrame(result)
        except Exception as e:
            print(f"根据日期获取龙虎榜数据失败: {e}")
            return pd.DataFrame()
    
    def get_lhb_data_by_code(self, code):
        """根据股票代码获取龙虎榜数据
        
        Args:
            code (str): 股票代码
            
        Returns:
            pandas.DataFrame: 龙虎榜数据
        """
        try:
            query_sql = """
            SELECT * FROM 龙虎榜详情
            WHERE 代码 = %s
            ORDER BY 上榜日 DESC
            """
            result = self.pg_manager.query(query_sql, (code,))
            return pd.DataFrame(result)
        except Exception as e:
            print(f"根据股票代码获取龙虎榜数据失败: {e}")
            return pd.DataFrame()
    
    def get_lhb_data_by_reason(self, reason):
        """根据上榜原因获取龙虎榜数据
        
        Args:
            reason (str): 上榜原因
            
        Returns:
            pandas.DataFrame: 龙虎榜数据
        """
        try:
            query_sql = """
            SELECT * FROM 龙虎榜详情
            WHERE 上榜原因 LIKE %s
            ORDER BY 上榜日 DESC, 涨跌幅 DESC
            """
            result = self.pg_manager.query(query_sql, (f'%{reason}%',))
            return pd.DataFrame(result)
        except Exception as e:
            print(f"根据上榜原因获取龙虎榜数据失败: {e}")
            return pd.DataFrame()
    
    def get_recent_lhb_data(self, days=7):
        """获取最近N天的龙虎榜数据
        
        Args:
            days (int, optional): 天数，默认为7天
            
        Returns:
            pandas.DataFrame: 龙虎榜数据
        """
        try:
            query_sql = """
            SELECT * FROM 龙虎榜详情
            WHERE 上榜日 >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY 上榜日 DESC, 涨跌幅 DESC
            """
            result = self.pg_manager.query(query_sql, (days,))
            return pd.DataFrame(result)
        except Exception as e:
            print(f"获取最近{days}天的龙虎榜数据失败: {e}")
            return pd.DataFrame()


# 主函数
if __name__ == "__main__":
    # 创建龙虎榜数据获取对象
    lhb_data = LhbData()
    
    # 增量更新龙虎榜数据（自动从数据库最后日期开始更新）
    update_result = lhb_data.update_lhb_data()
    
    if update_result:
        print("龙虎榜数据增量更新成功")
        
        # 获取最近10天的龙虎榜数据
        recent_data = lhb_data.get_recent_lhb_data(10)
        if not recent_data.empty:
            print(f"最近10天共有 {len(recent_data)} 条龙虎榜数据")
            print(recent_data.head())
    else:
        print("龙虎榜数据增量更新失败或无新数据")