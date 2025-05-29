#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
股票基本信息获取模块

获取A股股票的基本信息，包括股票代码、股票名称、市场、所属行业、市值等级、市盈率-动态、市净率、总市值、流通市值、60日均涨幅等
"""

import os
import sys
import pandas as pd
import numpy as np
import psycopg2
import psycopg2.extras
import yaml
from pathlib import Path
from tqdm import tqdm
import concurrent.futures

# 添加项目根目录到系统路径
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入AKShare
import akshare as ak


class StockBasicInfo:
    """股票基本信息获取类"""
    
    def __init__(self):
        """初始化数据库连接"""
        self.conn = None
        self.cursor = None
        self.config = self._load_config()
        self.connect_db()
        
    def _load_config(self):
        """加载数据库配置和表结构配置"""
        # 加载数据库连接配置
        connection_path = os.path.join(project_root, 'config', 'connection.yaml')
        with open(connection_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        # 加载表结构配置
        tables_path = os.path.join(project_root, 'config', 'tables.yaml')
        with open(tables_path, 'r', encoding='utf-8') as f:
            tables_config = yaml.safe_load(f)
            
        # 合并配置
        if 'tables' not in config:
            config['tables'] = tables_config['tables']
        return config
    
    def connect_db(self):
        """连接PostgreSQL数据库"""
        try:
            db_config = self.config['postgresql']
            self.conn = psycopg2.connect(
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['database'],
                user=db_config['user'],
                password=db_config['password']
            )
            self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            print("数据库连接成功")
        except Exception as e:
            print(f"数据库连接失败: {e}")
            sys.exit(1)
    
    def close_db(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("数据库连接已关闭")
    
    def get_market_type(self, stock_code):
        """根据股票代码判断市场类型
        
        Args:
            stock_code (str): 股票代码
            
        Returns:
            str: 市场类型，包括沪A、深A、创业、科创、京A
        """
        code = str(stock_code)
        if code.startswith('6'):
            return "沪A"
        elif code.startswith('0'):
            return "深A"
        elif code.startswith('3'):
            return "创业"
        elif code.startswith('68'):
            return "科创"
        else:
            return "京A"
    
    def get_market_cap_level(self, total_market_cap):
        """根据总市值确定市值等级
        
        Args:
            total_market_cap (float): 总市值（元）
            
        Returns:
            str: 市值等级，分为小盘股(0-20亿)、中盘股(20-500亿)、大盘股(500-1500亿)、超大盘股(>1500亿)
        """
        # 转换为亿元
        cap_in_billion = total_market_cap / 100000000
        
        if cap_in_billion <= 20:
            return "微盘股"
        elif cap_in_billion <= 500:
            return "小盘股"
        elif cap_in_billion <= 1500:
            return "中盘股"
        else:
            return "大盘股"
    
    def get_stock_industry(self):
        """获取行业板块信息
        
        使用并行处理方式获取各行业的成分股，提高效率
        
        Returns:
            dict: 股票代码到行业的映射字典
        """
        try:
            
            # 获取行业板块列表
            industry_list = ak.stock_board_industry_name_em()
            
            # 初始化股票行业映射字典
            stock_industry_dict = {}
            
            # 定义获取单个行业成分股的函数
            def get_industry_stocks(industry_code, industry_name):
                try:
                    # 获取该行业的成分股
                    industry_stocks = ak.stock_board_industry_cons_em(symbol=industry_code)
                    
                    # 构建该行业的股票映射
                    industry_dict = {}
                    for _, stock in industry_stocks.iterrows():
                        stock_code = stock['代码']
                        industry_dict[stock_code] = industry_name
                    
                    return industry_dict
                except Exception as e:
                    print(f"获取行业 {industry_name} 成分股失败: {e}")
                    return {}
            
            # 使用线程池并行获取各行业成分股
            max_workers = min(32, len(industry_list))  # 最大线程数，不超过行业数量
            print(f"开始并行获取 {len(industry_list)} 个行业的成分股信息...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交任务
                futures = {}
                for _, row in industry_list.iterrows():
                    industry_code = row['板块代码']
                    industry_name = row['板块名称']
                    future = executor.submit(get_industry_stocks, industry_code, industry_name)
                    futures[future] = industry_name
                
                # 使用tqdm显示进度条
                with tqdm(total=len(futures), desc="获取行业成分股", ncols=100) as pbar:
                    for future in concurrent.futures.as_completed(futures):
                        industry_name = futures[future]
                        pbar.update(1)
                        try:
                            # 获取任务结果并合并到总字典中
                            industry_dict = future.result()
                            stock_industry_dict.update(industry_dict)
                        except Exception as e:
                            print(f"处理行业 {industry_name} 失败: {e}")
            
            print(f"行业成分股获取完成，共获取 {len(stock_industry_dict)} 只股票的行业信息")
            return stock_industry_dict
        except Exception as e:
            print(f"获取行业信息失败: {e}")
            return {}

    
    def fetch_stock_basic_info(self):
        """获取A股股票基本信息
        
        Returns:
            pandas.DataFrame: 包含股票基本信息的DataFrame
        """
        try:
            # 获取A股股票实时行情数据
            stock_df = ak.stock_zh_a_spot_em()
            
            # 过滤掉退市和临退市的股票
            # 1. 过滤掉最新价为NaN的股票（退市或停牌）
            stock_df = stock_df[stock_df['流通市值'].notna()]
            
            # 2. 过滤掉名称中包含退市、*ST的股票
            #stock_df = stock_df[~stock_df['名称'].str.contains('退市|\*ST', regex=True)]
            
            print(f"过滤后剩余股票数量: {len(stock_df)}")
            
            # 获取行业信息
            industry_dict = self.get_stock_industry()
            
            # 添加市场类型列
            stock_df['市场'] = stock_df['代码'].apply(self.get_market_type)
            
            # 添加行业列
            stock_df['所属行业'] = stock_df['代码'].map(industry_dict)
            
            # 添加市值等级列
            stock_df['市值等级'] = stock_df['总市值'].apply(self.get_market_cap_level)
            
            # 计算60日均涨幅
            stock_df['60日均涨幅'] = stock_df['60日涨跌幅'] / 60
            
            # 选择需要的列
            result_df = stock_df[[
                '代码', '名称', '市场', '所属行业', '市值等级',
                '市盈率-动态', '市净率', '总市值', '流通市值', '60日均涨幅'
            ]]
            
            # 填充缺失值
            result_df = result_df.fillna({
                '所属行业': '未知行业',
                '市盈率-动态': 0,
                '市净率': 0,
                '60日均涨幅': 0
            })
            
            return result_df
        except Exception as e:
            print(f"获取股票基本信息失败: {e}")
            return pd.DataFrame()
    
    def create_table(self):
        """创建股票基本信息表"""
        try:
            # 获取表配置
            table_config = self.config['tables']['股票基本信息']
            table_name = table_config['name']
            
            # 创建表SQL
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS "{table_name}" (
                "股票代码" VARCHAR(10) PRIMARY KEY,
                "股票名称" VARCHAR(50) NOT NULL,
                "市场" VARCHAR(10),
                "所属行业" VARCHAR(50),
                "市值等级" VARCHAR(10),
                "市盈率-动态" FLOAT,
                "市净率" FLOAT,
                "总市值" FLOAT,
                "流通市值" FLOAT,
                "60日均涨幅" FLOAT,
                "更新时间" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            # 创建索引SQL
            create_index_sql = f"""
            CREATE INDEX IF NOT EXISTS idx_股票名称 ON "{table_name}" ("股票名称");
            CREATE INDEX IF NOT EXISTS idx_所属行业 ON "{table_name}" ("所属行业");
            CREATE INDEX IF NOT EXISTS idx_市值等级 ON "{table_name}" ("市值等级");
            """
            
            # 执行SQL
            self.cursor.execute(create_table_sql)
            self.cursor.execute(create_index_sql)
            self.conn.commit()
            print(f"表 {table_name} 创建成功")
        except Exception as e:
            self.conn.rollback()
            print(f"创建表失败: {e}")
    
    def save_to_db(self, df):
        """将股票基本信息保存到数据库
        
        Args:
            df (pandas.DataFrame): 股票基本信息DataFrame
        """
        if df.empty:
            print("没有数据需要保存")
            return
        
        try:
            # 获取表名
            table_name = self.config['tables']['股票基本信息']['name']
            
            # 先创建表
            self.create_table()
            
            # 准备插入数据
            records = df.to_dict('records')
            
            # 构建UPSERT语句（插入或更新）
            columns = ['股票代码', '股票名称', '市场', '所属行业', '市值等级', '市盈率-动态', '市净率', '总市值', '流通市值', '60日均涨幅']
            
            # 构建插入SQL
            insert_sql = f"""
            INSERT INTO "{table_name}" ("{'", "'.join(columns)}") 
            VALUES %s 
            ON CONFLICT ("股票代码") DO UPDATE SET 
            {', '.join([f'"{col}" = EXCLUDED."{col}"' for col in columns if col != '股票代码'])},
            "更新时间" = CURRENT_TIMESTAMP
            """
            
            # 准备数据
            values = [(r['代码'], r['名称'], r['市场'], r['所属行业'], r['市值等级'], 
                      r['市盈率-动态'], r['市净率'], r['总市值'], r['流通市值'], r['60日均涨幅']) for r in records]
            
            # 执行批量插入
            psycopg2.extras.execute_values(self.cursor, insert_sql, values)
            self.conn.commit()
            print(f"成功保存 {len(records)} 条股票基本信息到数据库")
        except Exception as e:
            self.conn.rollback()
            print(f"保存数据到数据库失败: {e}")
    
    def run(self):
        """运行股票基本信息获取和保存流程"""
        try:
            print("开始获取股票基本信息...")
            # 获取股票基本信息
            stock_info_df = self.fetch_stock_basic_info()
            
            if not stock_info_df.empty:
                # 保存到数据库
                self.save_to_db(stock_info_df)
                print("股票基本信息获取和保存完成")
            else:
                print("未获取到股票基本信息数据")
        except Exception as e:
            print(f"运行过程中发生错误: {e}")
        finally:
            # 关闭数据库连接
            self.close_db()


if __name__ == "__main__":
    # 创建实例并运行
    stock_basic_info = StockBasicInfo()
    stock_basic_info.run()