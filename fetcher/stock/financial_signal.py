#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
股票财务指标信号获取模块

获取A股股票的财务指标数据，包括按报告期、按年度、按单季度三种分区的数据
"""

import os
import sys
import pandas as pd
import numpy as np
import psycopg2
import psycopg2.extras
import yaml
from pathlib import Path
from datetime import datetime
import time
from tqdm import tqdm

# 添加项目根目录到系统路径
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入AKShare
import akshare as ak


class FinancialSignal:
    """股票财务指标信号获取类"""
    
    def __init__(self):
        """初始化数据库连接"""
        self.indicators = {
            "报告期": "按报告期",
            "年度": "按年度",
            "单季度": "按单季度"
        }
        self.conn = None
        self.cursor = None
        self.config = self._load_config()
        self.connect_db()
    
    def _load_config(self):
        """加载数据库配置"""
        config_path = os.path.join(project_root, 'config', 'connection.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 加载表结构配置
        tables_path = os.path.join(project_root, 'config', 'tables.yaml')
        with open(tables_path, 'r', encoding='utf-8') as f:
            tables_config = yaml.safe_load(f)
            
        # 合并配置
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
    
    def get_financial_indicator(self, symbol, indicator="按报告期"):
        """获取单个股票的财务指标数据
        
        Args:
            symbol (str): 股票代码，如000063
            indicator (str): 指标类型，可选值：按报告期、按年度、按单季度
            
        Returns:
            pandas.DataFrame: 财务指标数据
        """
        try:
            print(f"开始获取 {symbol} 的 {indicator} 财务指标数据...")
            if indicator not in self.indicators.values():
                print(f"不支持的指标类型: {indicator}，可选值: {list(self.indicators.values())}")
                return pd.DataFrame()
            
            # 调用AKShare接口获取数据
            start_time = time.time()
            df = ak.stock_financial_abstract_ths(symbol=symbol, indicator=indicator)
            end_time = time.time()
            print(f"API调用耗时: {end_time - start_time:.2f}秒")
            
            if df.empty:
                print(f"未获取到 {symbol} 的财务指标数据")
                return pd.DataFrame()
            
            # 确保报告期列是日期类型
            if '报告期' in df.columns:
                try:
                    df['报告期'] = pd.to_datetime(df['报告期'])
                except Exception as e:
                    print(f"报告期转换为日期类型失败: {e}")
            
            # 确保所有原始数据列都是字符串类型，以便正确存入数据库
            for col in df.columns:
                if col != '报告期':
                    df[col] = df[col].astype(str)
            
            return df
        except Exception as e:
            print(f"获取 {symbol} 的财务指标数据失败: {e}")
            return pd.DataFrame()
    
    def get_all_indicators(self, symbol):
        """获取单个股票的所有财务指标数据（按报告期、按年度、按单季度）
        
        Args:
            symbol (str): 股票代码，如000063
            
        Returns:
            dict: 包含三种指标类型数据的字典
        """
        result = {}
        for indicator_name, indicator_value in self.indicators.items():
            df = self.get_financial_indicator(symbol, indicator_value)
            if not df.empty:
                result[indicator_name] = df
        
        return result
    
    def merge_indicators(self, symbol):
        """合并单个股票的所有财务指标数据到一个表中
        
        Args:
            symbol (str): 股票代码，如000063
            
        Returns:
            pandas.DataFrame: 合并后的财务指标数据
        """
        indicators_data = self.get_all_indicators(symbol)
        if not indicators_data:
            return pd.DataFrame()
        
        # 创建一个空的DataFrame用于存储合并后的数据
        merged_df = pd.DataFrame()
        
        # 遍历所有指标类型的数据
        for indicator_name, df in indicators_data.items():
            if df.empty:
                continue
            
            # 添加指标类型列
            df['指标类型'] = indicator_name
            '''
            # 保留原始数据格式，只对处理后的列进行数值转换
            for col in df.columns:
                # 只处理处理后的数值列
                if col.endswith('_处理后'):
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            '''
            # 合并数据
            if merged_df.empty:
                merged_df = df.copy()
        '''    else:
                # 确保两个DataFrame有相同的列结构
                # 找出两个DataFrame中的所有列
                all_columns = set(merged_df.columns).union(set(df.columns))
                
                # 为缺失的列添加空值
                for col in all_columns:
                    if col not in merged_df.columns:
                        merged_df[col] = None
                    if col not in df.columns:
                        df[col] = None
                
                merged_df = pd.concat([merged_df, df], ignore_index=True)
        '''
        # 对合并后的数据按报告期排序
        if not merged_df.empty and '报告期' in merged_df.columns:
            # 确保报告期列是日期类型
            try:
                if not pd.api.types.is_datetime64_any_dtype(merged_df['报告期']):
                    merged_df['报告期'] = pd.to_datetime(merged_df['报告期'])
                merged_df = merged_df.sort_values('报告期', ascending=False).reset_index(drop=True)
            except Exception as e:
                print(f"排序报告期失败: {e}")
        
        return merged_df


    def get_stock_list(self):
        """从数据库获取股票列表
        
        Returns:
            list: 股票代码列表
        """
        try:
            # 从股票基本信息表获取股票列表
            query = """
            SELECT "股票代码", "股票名称", "市场" 
            FROM "股票基本信息"
            """
            self.cursor.execute(query)
            stocks = self.cursor.fetchall()
            
            # 转换为列表
            stock_list = []
            for stock in stocks:
                code = stock['股票代码']
                name = stock['股票名称']
                
                stock_list.append({
                    'code': code,
                    'name': name
                })
            
            return stock_list
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return []
    
    def create_financial_indicator_table(self):
        """创建财务指标表"""
        try:
            # 创建表SQL - 只创建基本结构，列会动态添加
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS "财务指标" (
                "股票代码" VARCHAR(10) NOT NULL,
                "报告期" DATE NOT NULL,
                "指标类型" VARCHAR(20) NOT NULL,
                "更新时间" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY ("股票代码", "报告期", "指标类型")
            );
            """
            
            # 创建索引SQL
            create_index_sql = """
            CREATE INDEX IF NOT EXISTS idx_financial_indicator_股票代码 ON "财务指标" ("股票代码");
            CREATE INDEX IF NOT EXISTS idx_financial_indicator_报告期 ON "财务指标" ("报告期");
            """
            
            # 执行SQL
            self.cursor.execute(create_table_sql)
            self.cursor.execute(create_index_sql)
            self.conn.commit()
            print("财务指标表创建成功")
        except Exception as e:
            self.conn.rollback()
            print(f"创建财务指标表失败: {e}")
            
    def _ensure_column_exists(self, column_name, column_type):
        """确保列存在于财务指标表中
        
        Args:
            column_name (str): 列名
            column_type (str): 列类型
        """
        try:
            # 检查列是否已存在
            check_column_sql = f"""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = '财务指标' AND column_name = '{column_name}';
            """
            self.cursor.execute(check_column_sql)
            column_exists = self.cursor.fetchone()
            
            if not column_exists:
                # 添加新列
                add_column_sql = f"""
                ALTER TABLE "财务指标" ADD COLUMN "{column_name}" {column_type};
                """
                self.cursor.execute(add_column_sql)
                self.conn.commit()  # 提交列添加操作
                print(f"添加新列: {column_name} 类型: {column_type}")
                return True
            return False
        except Exception as e:
            self.conn.rollback()
            print(f"确保列 {column_name} 存在失败: {e}")
            return False
    
    def save_financial_indicator_to_db(self, df, symbol):
        """将财务指标数据保存到数据库
        
        Args:
            df (pandas.DataFrame): 财务指标数据
            symbol (str): 股票代码
        """
        if df.empty:
            return
        
        try:
            # 先创建表
            self.create_financial_indicator_table()
            
            # 添加股票代码列
            df['股票代码'] = symbol
            
            # 处理NaT日期值
            if '报告期' in df.columns and pd.isna(df['报告期']).any():
                print(f"警告: {symbol} 存在无效的报告期日期，将被过滤")
                df = df.dropna(subset=['报告期'])
                
                if df.empty:
                    print(f"警告: {symbol} 过滤无效日期后没有数据，跳过")
                    return
                
            # 对数据进行去重，避免同一批次中有重复的主键值
            if not df.empty:
                print(f"去重前数据行数: {len(df)}")
                df = df.drop_duplicates(subset=['股票代码', '报告期', '指标类型'])
                print(f"去重后数据行数: {len(df)}")
                
                if df.empty:
                    print(f"警告: {symbol} 去重后没有数据，跳过")
                    return
            
            # 准备插入数据
            records = df.to_dict('records')
            
            # 获取列名
            columns = list(df.columns)
            
            # 先创建所有需要的列，确保表结构完整
            for col in df.columns:
                if col not in ['股票代码', '报告期', '指标类型', '更新时间']:
                    # 根据列名判断数据类型
                    column_type = "VARCHAR(50)"  # 默认为文本类型
                    
                    # 使用辅助方法确保列存在
                    self._ensure_column_exists(col, column_type)
            
            # 构建UPSERT语句（插入或更新）
            columns_quoted = [f'"{col}"' for col in columns]
            columns_str = ', '.join(columns_quoted)
            
            # 构建更新部分
            update_parts = []
            for col in columns:
                if col not in ['股票代码', '报告期', '指标类型']:
                    update_parts.append(f'"{col}" = EXCLUDED."{col}"')
            
            update_str = ', '.join(update_parts)
            
            # 确保表已经创建并有主键约束
            self.cursor.execute("""SELECT constraint_name FROM information_schema.table_constraints 
                               WHERE table_name = '财务指标' AND constraint_type = 'PRIMARY KEY'""")
            pk_exists = self.cursor.fetchone()
            
            if not pk_exists:
                print("警告: 表缺少主键约束，尝试添加主键约束")
                try:
                    self.cursor.execute('ALTER TABLE "财务指标" ADD PRIMARY KEY ("股票代码", "报告期", "指标类型")')
                    self.conn.commit()
                    print("已添加主键约束")
                except Exception as e:
                    print(f"添加主键约束失败: {e}")
            
            # 获取表中已存在的列
            self.cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = '财务指标';
            """)
            existing_columns = [row[0] for row in self.cursor.fetchall()]
            
            # 只使用表中已存在的列
            valid_columns = [col for col in columns if col.lower() in [c.lower() for c in existing_columns]]
            columns_quoted = [f'"{col}"' for col in valid_columns]
            columns_str = ', '.join(columns_quoted)
            
            # 构建更新部分
            update_parts = []
            for col in valid_columns:
                if col not in ['股票代码', '报告期', '指标类型']:
                    update_parts.append(f'"{col}" = EXCLUDED."{col}"')
            
            update_str = ', '.join(update_parts) if update_parts else '"更新时间" = CURRENT_TIMESTAMP'
            
            insert_sql = f"""
            INSERT INTO "财务指标" ({columns_str}) 
            VALUES %s 
            ON CONFLICT ("股票代码", "报告期", "指标类型") DO UPDATE SET 
            {update_str},
            "更新时间" = CURRENT_TIMESTAMP
            """
            
            # 逐行插入数据，避免批量插入时的主键冲突
            success_count = 0
            error_count = 0
            
            for record in records:
                try:
                    # 创建一个新的SQL语句，使用参数化查询而不是直接拼接值
                    columns_list = [f'"{col}"' for col in valid_columns]
                    placeholders = [f'%s' for _ in valid_columns]
                    
                    insert_sql_single = f"INSERT INTO \"财务指标\" ({', '.join(columns_list)}) VALUES ({', '.join(placeholders)}) ON CONFLICT (\"股票代码\", \"报告期\", \"指标类型\") DO UPDATE SET {update_str}, \"更新时间\" = CURRENT_TIMESTAMP"
                    
                    # 准备参数值
                    params = []
                    for col in valid_columns:
                        value = record.get(col)
                        # 对于日期列，确保是日期类型
                        if col == '报告期':
                            # 确保日期以正确的格式传递给数据库
                            if isinstance(value, pd.Timestamp):
                                params.append(value.strftime('%Y-%m-%d'))
                            else:
                                params.append(value)
                        # 对于其他所有列，包括原始数据列，直接作为字符串处理
                        elif value == 'False' or value is False:
                            params.append(None)
                        else:
                            params.append(value)
                            
                    # 执行单行插入
                    self.cursor.execute(insert_sql_single, params)
                    self.conn.commit()
                    success_count += 1
                except Exception as e:
                    self.conn.rollback()
                    error_count += 1
                    if error_count < 5:  # 只打印前几个错误，避免日志过多
                        print(f"插入单条记录失败: {e}")
            
            print(f"成功插入 {success_count} 条记录，失败 {error_count} 条记录")
        except Exception as e:
            self.conn.rollback()
            print(f"保存财务指标数据到数据库失败: {e}")
    
    def fetch_and_save_financial_indicators(self, limit=None):
        """获取并保存所有股票的财务指标数据
        
        Args:
            limit (int, optional): 限制处理的股票数量，用于测试。默认为None，表示处理所有股票。
        """
        try:
            # 获取股票列表
            stock_list = self.get_stock_list()
            
            if limit:
                stock_list = stock_list[:limit]
            
            print(f"开始获取 {len(stock_list)} 只股票的财务指标数据...")
            
            # 使用tqdm创建进度条
            for stock in tqdm(stock_list, desc="处理进度"):
                code = stock['code']
                name = stock['name']
                
                try:
                    # 获取合并后的财务指标数据
                    merged_df = self.merge_indicators(code)
                    
                    if not merged_df.empty:
                        # 保存到数据库
                        self.save_financial_indicator_to_db(merged_df, code)
                    else:
                        print(f"{code} {name} 没有财务指标数据")
                except Exception as e:
                    print(f"{code} {name} 处理失败: {e}")
                
                # 避免频繁请求导致被封IP
                time.sleep(0.2)
            
            print("所有股票的财务指标数据获取和保存完成")
        except Exception as e:
            print(f"获取和保存财务指标数据过程中发生错误: {e}")
    
    def run(self, limit=None):
        """运行财务指标数据获取和保存流程
        
        Args:
            limit (int, optional): 限制处理的股票数量，用于测试。默认为None，表示处理所有股票。
        """
        try:
            print("开始获取股票财务指标数据...")
            # 获取并保存财务指标数据
            self.fetch_and_save_financial_indicators(limit)
            print("股票财务指标数据获取和保存完成")
        except Exception as e:
            print(f"运行过程中发生错误: {e}")
        finally:
            # 关闭数据库连接
            self.close_db()


def main():
    """主函数，用于测试"""
    # 创建实例并运行，可以设置limit参数限制处理的股票数量，用于测试
    financial_signal = FinancialSignal()
    financial_signal.run(limit=None)  # 测试时处理股票量


if __name__ == "__main__":
    main()