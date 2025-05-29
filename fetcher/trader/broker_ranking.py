#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
营业部统计数据获取模块

获取A股市场龙虎榜营业部统计数据，包括上榜次数最多、资金实力最强和抱团操作实力
属于交易者数据获取模块的一部分

优化说明：
1. 识别并处理不同接口中的相同数据字段，避免重复保存
   - stock_lh_yyb_most提供的'上榜次数'与stock_lh_yyb_capital的'今日最高操作'是相同的数据
   - stock_lh_yyb_most提供的'合计动用资金'与stock_lh_yyb_capital的'累计参与金额'是相同的数据
2. 使用字段映射关系统一处理相同数据
3. 在数据库更新时，使用COALESCE确保已有数据不被覆盖
"""

import os
import sys
import pandas as pd
import numpy as np
import psycopg2
import psycopg2.extras
import yaml
from pathlib import Path
from datetime import datetime, timedelta
import time

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入AKShare
import akshare as ak


class BrokerRanking:
    """营业部统计数据获取类"""
    
    def __init__(self):
        """初始化数据库连接"""
        self.conn = None
        self.cursor = None
        self.config = self._load_config()
        self.connect_db()
        
        # 定义字段映射关系，标识不同接口中相同的数据字段
        self.field_mapping = {
            "今日最高操作": "上榜次数",  # 这两个字段是相同的数据
            "累计参与金额": "合计动用资金"  # 这两个字段是相同的数据
        }
        
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
    
    def create_broker_ranking_table(self):
        """创建营业部统计表"""
        try:
            # 创建表SQL - 调整数据类型以适应实际数据
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS "营业部统计" (
                "营业部名称" VARCHAR(100) NOT NULL,
                "上榜次数" VARCHAR(20),  -- 可能包含文本标签如"一线游资"
                "合计动用资金" FLOAT,
                "年内上榜次数" INTEGER,
                "年内买入股票只数" INTEGER,
                "年内3日跟买成功率" VARCHAR(20),  -- 百分比字段
                "今日最高金额" FLOAT,
                "今日最高买入金额" FLOAT,
                "累计买入金额" FLOAT,
                "携手营业部家数" INTEGER,
                "年内最佳携手对象" VARCHAR(100),
                "年内最佳携手股票数" INTEGER,
                "年内最佳携手成功率" VARCHAR(20),  -- 百分比字段
                "更新时间" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY ("营业部名称")
            );
            """
            
            # 先删除旧表，以便应用新的表结构
            drop_table_sql = "DROP TABLE IF EXISTS \"营业部统计\";"
            self.cursor.execute(drop_table_sql)
            
            # 创建索引SQL
            create_index_sql = """
            CREATE INDEX IF NOT EXISTS idx_broker_ranking_营业部名称 ON "营业部统计" ("营业部名称");
            """
            
            # 执行SQL
            self.cursor.execute(create_table_sql)
            self.cursor.execute(create_index_sql)
            self.conn.commit()
            print("营业部统计表创建成功")
        except Exception as e:
            self.conn.rollback()
            print(f"创建营业部统计表失败: {e}")
            # 打印详细错误信息以便调试
            import traceback
            print(traceback.format_exc())
    
    def fetch_broker_most_active(self):
        """获取上榜次数最多的营业部统计
        
        Returns:
            pandas.DataFrame: 上榜次数最多的营业部统计数据
        """
        try:
            # 从AKShare获取数据
            df = ak.stock_lh_yyb_most()
            
            if df.empty:
                print("未获取到上榜次数最多的营业部统计数据")
                return pd.DataFrame()
            
            # 打印原始数据的列和样本，便于调试
            print(f"上榜次数最多的营业部统计数据列: {df.columns.tolist()}")
            print(f"上榜次数最多的营业部统计数据样本:\n{df.head(2)}")
            
            # 处理上榜次数列 - 可能包含文本标签如"一线游资"
            if "上榜次数" in df.columns:
                # 保留原始文本格式，不进行数值转换
                # 如果需要数值分析，可以在应用层面进行处理
                pass
            
            # 定义安全的数值转换函数
            def safe_convert_money(x):
                try:
                    if isinstance(x, str):
                        if "亿" in x:
                            return float(x.replace("亿", "")) * 10000
                        elif "万" in x:
                            return float(x.replace("万", ""))
                    return pd.to_numeric(x, errors='coerce')
                except Exception as e:
                    print(f"转换金额失败: 值='{x}', 错误={e}")
                    return np.nan

            # 处理合计动用资金列
            if "合计动用资金" in df.columns:
                df["合计动用资金"] = df["合计动用资金"].apply(safe_convert_money)
                null_count = df["合计动用资金"].isnull().sum()
                if null_count > 0:
                    print(f"警告: 清洗后 合计动用资金 列有 {null_count} 个空值")
            
            # 处理年内上榜次数和年内买入股票只数 - 转换为数值类型，无法转换的设为 NaN
            for col in ["年内上榜次数", "年内买入股票只数"]:
                if col in df.columns:
                    original_nulls = df[col].isnull().sum()
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    new_nulls = df[col].isnull().sum()
                    if new_nulls > original_nulls:
                        print(f"警告: 清洗后 {col} 列空值增加 {new_nulls - original_nulls} 个")
                else:
                    # Corrected warning message (ranking_type is not available here)
                    print(f"警告: '上榜次数最多' 数据缺少列: {col}") 
                    df[col] = np.nan # 如果列不存在，则添加并填充 NaN

            # 处理年内3日跟买成功率 - 保留为字符串格式
            if "年内3日跟买成功率" in df.columns:
                df["年内3日跟买成功率"] = df["年内3日跟买成功率"].astype(str)
            
            # 在返回前将 NaN 替换为 None
            df = df.replace({np.nan: None})

            # 返回处理后的数据框
            return df
        except Exception as e:
            print(f"获取上榜次数最多的营业部统计数据失败: {e}")
            import traceback
            print(traceback.format_exc())
            return pd.DataFrame()
    
    def fetch_broker_capital_strength(self):
        """获取资金实力最强的营业部统计
        
        注意：此接口中的'今日最高操作'与'上榜次数最多'接口中的'上榜次数'是相同的数据
        '累计参与金额'与'合计动用资金'也是相同的数据，避免重复保存
        
        Returns:
            pandas.DataFrame: 资金实力最强的营业部统计数据
        """
        try:
            # 从AKShare获取数据
            df = ak.stock_lh_yyb_capital()
            
            if df.empty:
                print("未获取到资金实力最强的营业部统计数据")
                return pd.DataFrame()
            
            # 打印原始数据的列和样本，便于调试
            print(f"资金实力最强的营业部统计数据列: {df.columns.tolist()}")
            print(f"资金实力最强的营业部统计数据样本:\n{df.head(2)}")
            
            # 处理今日最高操作列 - 可能包含文本标签如"一线游资"
            # 注意：此列与'上榜次数最多'接口中的'上榜次数'是相同的数据
            if "今日最高操作" in df.columns:
                # 今日最高操作是文本字段，保留原样
                df["今日最高操作"] = df["今日最高操作"].astype(str)
            
            # 定义安全的数值转换函数 (复用)
            def safe_convert_money(x):
                try:
                    if isinstance(x, str):
                        if "亿" in x:
                            return float(x.replace("亿", "")) * 10000
                        elif "万" in x:
                            return float(x.replace("万", ""))
                    return pd.to_numeric(x, errors='coerce')
                except Exception as e:
                    print(f"转换金额失败: 值='{x}', 错误={e}")
                    return np.nan

            # 处理金额列
            # 注意：'累计参与金额'与'上榜次数最多'接口中的'合计动用资金'是相同的数据
            for col in ["今日最高金额", "今日最高买入金额", "累计参与金额", "累计买入金额"]:
                if col in df.columns:
                    df[col] = df[col].apply(safe_convert_money)
                    null_count = df[col].isnull().sum()
                    if null_count > 0:
                        print(f"警告: 清洗后 {col} 列有 {null_count} 个空值")
            
            # 在返回前将 NaN 替换为 None
            df = df.replace({np.nan: None})
            
            # 处理映射字段，确保相同数据使用统一的字段名
            # 将'今日最高操作'的值映射到'上榜次数'字段
            if '今日最高操作' in df.columns and '上榜次数' not in df.columns:
                df['上榜次数'] = df['今日最高操作']
            
            # 将'累计参与金额'的值映射到'合计动用资金'字段
            if '累计参与金额' in df.columns and '合计动用资金' not in df.columns:
                df['合计动用资金'] = df['累计参与金额']
            
            # 返回处理后的数据框
            return df
        except Exception as e:
            print(f"获取资金实力最强的营业部统计数据失败: {e}")
            import traceback
            print(traceback.format_exc())
            return pd.DataFrame()
    
    def fetch_broker_control_strength(self):
        """获取抱团操作实力的营业部统计
        
        Returns:
            pandas.DataFrame: 抱团操作实力的营业部统计数据
        """
        try:
            # 从AKShare获取数据
            df = ak.stock_lh_yyb_control()
            
            if df.empty:
                print("未获取到抱团操作实力的营业部统计数据")
                return pd.DataFrame()
            
            # 打印原始数据的列和样本，便于调试
            print(f"抱团操作实力的营业部统计数据列: {df.columns.tolist()}")
            print(f"抱团操作实力的营业部统计数据样本:\n{df.head(2)}")
            
            # 处理携手营业部家数和年内最佳携手股票数
            for col in ["携手营业部家数", "年内最佳携手股票数"]:
                if col in df.columns:
                    original_nulls = df[col].isnull().sum()
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    new_nulls = df[col].isnull().sum()
                    if new_nulls > original_nulls:
                        print(f"警告: 清洗后 {col} 列空值增加 {new_nulls - original_nulls} 个")
            
            # 处理年内最佳携手成功率 - 保留百分比字符串格式
            if "年内最佳携手成功率" in df.columns:
                df["年内最佳携手成功率"] = df["年内最佳携手成功率"].astype(str)
            
            # 处理年内最佳携手对象 - 确保是字符串类型
            if "年内最佳携手对象" in df.columns:
                df["年内最佳携手对象"] = df["年内最佳携手对象"].astype(str)
            
            # 返回处理后的数据框
            return df
        except Exception as e:
            print(f"获取抱团操作实力的营业部统计数据失败: {e}")
            import traceback
            print(traceback.format_exc())
            return pd.DataFrame()
    
    def _save_broker_ranking_to_db(self, df, ranking_type):
        """将营业部统计数据保存到数据库
        
        Args:
            df (pandas.DataFrame): 营业部统计数据
            ranking_type (str): 排行类型，包括上榜次数最多、资金实力最强、抱团操作实力
        """
        try:
            # 检查表是否存在，不存在则创建
            self.cursor.execute("SELECT to_regclass('营业部统计')")
            if not self.cursor.fetchone()[0]:
                self.create_broker_ranking_table()
            
            # 移除序号列（如果存在）
            if "序号" in df.columns:
                df = df.drop("序号", axis=1)

            # 定义不同排行类型对应的列
            # 注意：避免重复保存相同数据
            # stock_lh_yyb_most提供的'上榜次数'与stock_lh_yyb_capital的'今日最高操作'是相同的数据
            # '合计动用资金'与'累计参与金额'也是相同的数据
            ranking_columns = {
                "上榜次数最多": ["上榜次数", "合计动用资金", "年内上榜次数", "年内买入股票只数", "年内3日跟买成功率"],
                "资金实力最强": ["今日最高金额", "今日最高买入金额", "累计买入金额"],  # 移除了'今日最高操作'和'累计参与金额'
                "抱团操作实力": ["携手营业部家数", "年内最佳携手对象", "年内最佳携手股票数", "年内最佳携手成功率"]
            }

            # 获取当前排行类型对应的列，并过滤掉DataFrame中不存在的列
            update_columns = [col for col in ranking_columns.get(ranking_type, []) if col in df.columns]
            
            # 获取 DataFrame 中实际存在的列 (包括主键 '营业部名称')
            insert_columns = [col for col in df.columns if col == '营业部名称' or col in update_columns]
            # 确保 '营业部名称' 在第一位
            if '营业部名称' in insert_columns:
                insert_columns.remove('营业部名称')
                insert_columns.insert(0, '营业部名称')
            else:
                print(f"错误: {ranking_type} 数据缺少主键 '营业部名称'，无法保存")
                return # 如果没有主键，则无法保存

            # 添加 '更新时间' 列到插入和更新列表
            if '更新时间' not in insert_columns:
                 insert_columns.append('更新时间')
            if '更新时间' not in update_columns:
                 update_columns.append('更新时间')

            # 构建插入列名和占位符字符串
            insert_cols_sql = '", "'.join(insert_columns)
            values_placeholders = ', '.join(['%s'] * len(insert_columns))

            # 准备数据
            for _, row in df.iterrows():
                # 构建 SET 子句 (只更新当前类型相关的列)
                set_clauses = []
                for col in update_columns:
                    # EXCLUDED 引用的是 VALUES 子句中对应位置的值
                    # 需要找到 col 在 insert_columns 中的索引来引用正确的值
                    try:
                        # 检查当前列是否是映射字段（在不同接口中有相同数据的字段）
                        is_mapped_field = col in self.field_mapping.keys() or col in self.field_mapping.values()
                        
                        # 对于映射字段，只有当数据库中该字段为NULL时才更新，避免覆盖已有数据
                        if is_mapped_field:
                            # 使用COALESCE确保只有在目标字段为NULL时才更新
                            set_clauses.append(f'"{col}" = COALESCE("营业部统计"."{col}", EXCLUDED."{col}")')
                            
                            # 如果是映射源字段，还需要检查是否需要更新对应的目标字段
                            if col in self.field_mapping:
                                mapped_col = self.field_mapping[col]
                                # 如果目标字段为NULL但源字段有值，则用源字段值更新目标字段
                                set_clauses.append(f'"{mapped_col}" = CASE WHEN "营业部统计"."{mapped_col}" IS NULL THEN EXCLUDED."{col}" ELSE "营业部统计"."{mapped_col}" END')
                        else:
                            # 其他字段正常更新
                            set_clauses.append(f'"{col}" = EXCLUDED."{col}"')
                    except ValueError:
                        # If the column is in update_columns but not insert_columns (should not happen)
                        # Skip this column for safety
                        print(f"警告: 列 '{col}' 在 update_columns 但不在 insert_columns 中，跳过更新")
                        continue
                
                set_sql = ", ".join(set_clauses)

                # 构建插入或更新的SQL
                # Remove the unnecessary 'AS v(...)' alias
                sql = f"""
                INSERT INTO "营业部统计" ("{insert_cols_sql}") 
                VALUES ({values_placeholders})
                ON CONFLICT ("营业部名称") DO UPDATE SET 
                    {set_sql}
                """
                
                # 准备参数列表，只包含 insert_columns 对应的值
                params_list = []
                for col in insert_columns:
                    if col == '更新时间':
                        params_list.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    else:
                        # 从 row 中获取值，并将 NaN 替换为 None
                        value = row.get(col)
                        params_list.append(None if pd.isna(value) else value)

                params = tuple(params_list)
                
                # 执行SQL
                try:
                    self.cursor.execute(sql, params)
                except Exception as exec_error:
                    print(f"执行SQL失败: {exec_error}")
                    print(f"SQL: {self.cursor.mogrify(sql, params).decode('utf-8')}") # 打印格式化后的SQL
                    # 可以选择继续或中断
                    # continue
                    raise # 重新抛出异常以便上层捕获
            
            # 提交事务
            self.conn.commit()
            print(f"{ranking_type}营业部统计数据保存成功")
        except Exception as e:
            self.conn.rollback()
            print(f"保存{ranking_type}营业部统计数据失败: {e}")
            import traceback
            print(traceback.format_exc())
    
    def fetch_all_broker_rankings(self):
        """获取所有类型的营业部统计数据并分别保存"""
        try:
            # 创建表（如果不存在）
            self.create_broker_ranking_table()
            
            all_data_fetched = True
            fetched_data = {}

            # 获取并保存 上榜次数最多的 数据
            # 注意：这个接口提供的'上榜次数'和'合计动用资金'是基础数据，应该优先保存
            print("开始获取并保存 上榜次数最多的 营业部统计数据...")
            most_active_df = self.fetch_broker_most_active()
            if not most_active_df.empty:
                self._save_broker_ranking_to_db(most_active_df, "上榜次数最多")
                fetched_data["上榜次数最多"] = most_active_df
            else:
                print("未能获取到 上榜次数最多的 营业部统计数据")
                all_data_fetched = False

            # 获取并保存 资金实力最强的 数据
            # 注意：这个接口的'今日最高操作'与'上榜次数'相同，'累计参与金额'与'合计动用资金'相同
            # 我们只保存其独有的字段，避免覆盖已有数据
            print("开始获取并保存 资金实力最强的 营业部统计数据...")
            capital_strength_df = self.fetch_broker_capital_strength()
            if not capital_strength_df.empty:
                # 如果已经保存了上榜次数最多的数据，则不再重复保存相同字段
                if "上榜次数最多" in fetched_data and not fetched_data["上榜次数最多"].empty:
                    print("已保存上榜次数最多数据，资金实力最强数据中的重叠字段将不覆盖已有数据")
                self._save_broker_ranking_to_db(capital_strength_df, "资金实力最强")
                fetched_data["资金实力最强"] = capital_strength_df
            else:
                print("未能获取到 资金实力最强的 营业部统计数据")
                all_data_fetched = False

            # 获取并保存 抱团操作实力的 数据
            print("开始获取并保存 抱团操作实力的 营业部统计数据...")
            control_strength_df = self.fetch_broker_control_strength()
            if not control_strength_df.empty:
                self._save_broker_ranking_to_db(control_strength_df, "抱团操作实力")
                fetched_data["抱团操作实力"] = control_strength_df
            else:
                print("未能获取到 抱团操作实力的 营业部统计数据")
                all_data_fetched = False

            if not fetched_data:
                print("未能获取到任何营业部统计数据")
                # 可以考虑返回一个空字典或根据需要抛出异常
                return {}
                
            print("所有可用的营业部统计数据已获取并保存。")
            return fetched_data # 返回获取到的数据字典

        except Exception as e:
            print(f"获取并保存所有营业部统计数据失败: {e}")
            import traceback
            print(traceback.format_exc())
            return {} # 返回空字典表示失败


if __name__ == "__main__":
    # 测试代码
    broker_ranking = BrokerRanking()
    rankings = broker_ranking.fetch_all_broker_rankings()
    
    # 打印结果
    for ranking_type, df in rankings.items():
        if not df.empty:
            print(f"\n{ranking_type}营业部统计数据示例（前5条）:")
            print(df.head())
    
    # 关闭数据库连接
    broker_ranking.close_db()