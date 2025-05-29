# -*- coding: utf-8 -*-

"""
衍生指标计算模块

读取股票、行业、指数的基础数据和技术指标，计算衍生指标，
并将结果存储到数据库中。

特点：
1. 支持不同类型实体（股票、行业、指数）的衍生指标计算
2. 采用可扩展的设计，便于添加新的衍生指标
3. 支持批量处理多个实体
4. 支持指定日期范围的数据处理
"""

import os
import sys
import pandas as pd
import numpy as np
import logging
import importlib
import inspect
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Union, Optional, Any, Tuple

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入项目模块
from db.table_data_reader import TableDataReader
from db.postgresql_manager import PostgreSQLManager
from utils.config_loader import load_connection_config
from utils.performance_monitor import performance_monitor
from core.analyzer.derived_indicator_loader import get_indicator_loader, indicator

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DerivedIndicatorCalculator:
    """衍生指标计算器
    
    用于计算股票、行业、指数的衍生指标，并将结果存储到数据库中。
    衍生指标是基于基础数据和技术指标计算得出的更复杂的指标。
    
    特点：
    1. 支持不同类型实体的衍生指标计算
    2. 采用可扩展的设计，便于添加新的衍生指标
    3. 支持批量处理多个实体
    4. 支持指定日期范围的数据处理
    """

    def __init__(self, db_config=None, dry_run=False):
        """初始化衍生指标计算器
        
        Args:
            db_config (dict, optional): 数据库连接配置，如果为None则自动加载
            dry_run (bool, optional): 如果为True，则不执行数据库写入操作
        """
        self.dry_run = dry_run
        
        # 加载数据库配置
        if db_config is None:
            self.db_config = load_connection_config()
        else:
            self.db_config = db_config
            
        # 初始化数据库连接
        self.pg_manager = PostgreSQLManager(**self.db_config.get('postgresql', {}))
        
        # 初始化数据读取器
        self.reader = TableDataReader()
        
        # 获取指标加载器
        self.indicator_loader = get_indicator_loader()
        
        # 实体类型配置
        self.entity_config = {
            'stock': {
                'table_name': self.indicator_loader.get_entity_history_table('stock'),
                'id_column': self.indicator_loader.get_entity_id_column('stock'),
                'derived_table': self.indicator_loader.get_entity_table_name('stock'),
                'indicators': self.indicator_loader.get_all_indicators('stock')
            },
            'industry': {
                'table_name': self.indicator_loader.get_entity_history_table('industry'),
                'id_column': self.indicator_loader.get_entity_id_column('industry'),
                'derived_table': self.indicator_loader.get_entity_table_name('industry'),
                'indicators': self.indicator_loader.get_all_indicators('industry')
            },
            'index': {
                'table_name': self.indicator_loader.get_entity_history_table('index'),
                'id_column': self.indicator_loader.get_entity_id_column('index'),
                'derived_table': self.indicator_loader.get_entity_table_name('index'),
                'indicators': self.indicator_loader.get_all_indicators('index')
            }
        }
        
        # 初始化衍生指标表（如果不存在）
        if not dry_run:
            self._init_derived_indicator_tables()
    
    def _init_derived_indicator_tables(self):
        """初始化衍生指标表
        
        如果衍生指标表不存在，则创建表结构
        """
        # 检查并创建股票衍生指标表
        if not self.pg_manager.table_exists('股票衍生指标'):
            self._create_derived_indicator_table('stock')
            
        # 检查并创建行业衍生指标表
        if not self.pg_manager.table_exists('行业衍生指标'):
            self._create_derived_indicator_table('industry')
            
        # 检查并创建指数衍生指标表
        if not self.pg_manager.table_exists('指数衍生指标'):
            self._create_derived_indicator_table('index')
    
    def _create_derived_indicator_table(self, entity_type):
        """创建衍生指标表
        
        Args:
            entity_type (str): 实体类型 ('stock', 'industry', 'index')
        """
        config = self.entity_config[entity_type]
        table_name = config['derived_table']
        id_column = config['id_column']
        
        # 获取表配置
        table_config = self.indicator_loader.get_table_config(table_name)
        
        if table_config:
            # 从配置文件构建SQL
            columns_sql = []
            
            # 添加主键列
            for col_name, col_config in table_config['columns'].items():
                col_type = col_config.get('type', 'VARCHAR(50)')
                is_primary = col_config.get('primary_key', False)
                default = col_config.get('default', None)
                not_null = 'NOT NULL' if is_primary or col_config.get('not_null', False) else ''
                default_sql = f"DEFAULT {default}" if default else ''
                
                columns_sql.append(f"\"{col_name}\" {col_type} {not_null} {default_sql}".strip())
            
            # 添加指标列
            common_indicators = self.indicator_loader.config.get('common_indicators', {})
            entity_indicators = self.indicator_loader.config.get(f"{entity_type}_indicators", {})
            
            # 合并通用指标和实体特有指标
            all_indicators = {**common_indicators, **entity_indicators}
            
            for ind_name, ind_config in all_indicators.items():
                col_type = ind_config.get('type', 'FLOAT')
                default = ind_config.get('default', None)
                default_sql = f"DEFAULT {default}" if default is not None else ''
                
                columns_sql.append(f"\"{ind_name}\" {col_type} {default_sql}".strip())
            
            # 构建主键
            primary_key_cols = [col_name for col_name, col_config in table_config['columns'].items() 
                               if col_config.get('primary_key', False)]
            primary_key_sql = f"PRIMARY KEY ({', '.join([f'\"{col}\"' for col in primary_key_cols])})" if primary_key_cols else ''
            
            # 构建完整SQL
            sql = f"""
            CREATE TABLE IF NOT EXISTS \"{table_name}\" (
                {',\n                '.join(columns_sql)}
                {f',\n                {primary_key_sql}' if primary_key_sql else ''}
            );
            """
            
            # 添加索引
            indexes_sql = ''
            if 'indexes' in table_config:
                for index in table_config['indexes']:
                    index_name = index['name']
                    index_columns = ', '.join([f'\"{col}\"' for col in index['columns']])
                    indexes_sql += f"CREATE INDEX IF NOT EXISTS {index_name} ON \"{table_name}\" ({index_columns});\n"
            
            sql += indexes_sql
        else:
            # 使用默认SQL
            if entity_type == 'stock':
                sql = f"""
                CREATE TABLE IF NOT EXISTS \"{table_name}\" (
                    \"{id_column}\" VARCHAR(10) NOT NULL,
                    \"日期\" DATE NOT NULL,
                    \"golden_cross\" SMALLINT,
                    \"death_cross\" SMALLINT,
                    \"rsi_overbought\" SMALLINT,
                    \"rsi_oversold\" SMALLINT,
                    \"macd_golden_cross\" SMALLINT,
                    \"macd_death_cross\" SMALLINT,
                    \"updated_at\" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (\"{id_column}\", \"日期\")
                );
                CREATE INDEX IF NOT EXISTS idx_{table_name}_date ON \"{table_name}\" (\"日期\");
                """
            elif entity_type == 'industry':
                sql = f"""
                CREATE TABLE IF NOT EXISTS \"{table_name}\" (
                    \"{id_column}\" VARCHAR(50) NOT NULL,
                    \"日期\" DATE NOT NULL,
                    \"golden_cross\" SMALLINT,
                    \"death_cross\" SMALLINT,
                    \"rsi_overbought\" SMALLINT,
                    \"rsi_oversold\" SMALLINT,
                    \"macd_golden_cross\" SMALLINT,
                    \"macd_death_cross\" SMALLINT,
                    \"industry_strength\" FLOAT,
                    \"updated_at\" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (\"{id_column}\", \"日期\")
                );
                CREATE INDEX IF NOT EXISTS idx_{table_name}_date ON \"{table_name}\" (\"日期\");
                """
            else:  # index
                sql = f"""
                CREATE TABLE IF NOT EXISTS \"{table_name}\" (
                    \"{id_column}\" VARCHAR(10) NOT NULL,
                    \"日期\" DATE NOT NULL,
                    \"golden_cross\" SMALLINT,
                    \"death_cross\" SMALLINT,
                    \"rsi_overbought\" SMALLINT,
                    \"rsi_oversold\" SMALLINT,
                    \"macd_golden_cross\" SMALLINT,
                    \"macd_death_cross\" SMALLINT,
                    \"market_breadth\" FLOAT,
                    \"updated_at\" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (\"{id_column}\", \"日期\")
                );
                CREATE INDEX IF NOT EXISTS idx_{table_name}_date ON \"{table_name}\" (\"日期\");
                """
        
        # 执行SQL
        try:
            self.pg_manager.execute(sql)
            logger.info(f"创建{table_name}表成功")
        except Exception as e:
            logger.error(f"创建{table_name}表失败: {e}")
            raise
    
    def run(self, data_types=None, entity_ids_map=None, specific_entities=None):
        """运行衍生指标计算的主函数

        Args:
            data_types (list, optional): 要处理的数据类型列表 ('stock', 'industry', 'index'). 
                                         如果为 None, 则处理所有类型。
            entity_ids_map (dict, optional): 一个字典，键是数据类型，值是该类型的实体ID列表。
                                           例如: {'stock': ['000001', '000002']}
            specific_entities (dict, optional): 与entity_ids_map相同，为了兼容性保留
        """
        # 如果没有指定数据类型，则处理所有类型
        if data_types is None:
            data_types = list(self.entity_config.keys())
        
        # 如果specific_entities存在但entity_ids_map不存在，则使用specific_entities
        if entity_ids_map is None and specific_entities is not None:
            entity_ids_map = specific_entities
        
        # 获取当前日期作为结束日期
        end_date = datetime.now().strftime('%Y-%m-%d')
        # 默认处理最近一年的数据
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        # 处理每种数据类型
        for data_type in data_types:
            if data_type not in self.entity_config:
                logger.warning(f"未知的数据类型: {data_type}，跳过处理")
                continue
            
            # 如果指定了实体ID列表，则只处理这些实体
            if entity_ids_map and data_type in entity_ids_map:
                entity_ids = entity_ids_map[data_type]
                for entity_id in entity_ids:
                    self.process_entity(data_type, entity_id, start_date, end_date)
            else:
                # 否则处理所有实体
                self._process_all_entities(data_type, start_date, end_date)
    
    def _process_all_entities(self, data_type, start_date, end_date):
        """处理指定类型的所有实体
        
        Args:
            data_type (str): 实体类型 ('stock', 'industry', 'index')
            start_date (str): 开始日期
            end_date (str): 结束日期
        """
        config = self.entity_config[data_type]
        table_name = config['table_name']
        id_column = config['id_column']
        
        # 查询所有实体ID
        sql = f"SELECT DISTINCT \"{id_column}\" FROM \"{table_name}\""
        try:
            df = self.pg_manager.query_df(sql)
            if df.empty:
                logger.warning(f"未找到任何{data_type}实体")
                return
            
            entity_ids = df[id_column].tolist()
            logger.info(f"找到{len(entity_ids)}个{data_type}实体")
            
            # 处理每个实体
            for entity_id in entity_ids:
                self.process_entity(data_type, entity_id, start_date, end_date)
                
        except Exception as e:
            logger.error(f"查询{data_type}实体列表失败: {e}")
    
    def process_entity(self, entity_type, entity_id, start_date, end_date):
        """处理单个实体的衍生指标计算
        
        Args:
            entity_type (str): 实体类型 ('stock', 'industry', 'index')
            entity_id (str): 实体ID
            start_date (str): 开始日期
            end_date (str): 结束日期
        """
        logger.info(f"处理{entity_type} {entity_id} 从 {start_date} 到 {end_date}")
        
        try:
            # 获取实体配置
            config = self.entity_config[entity_type]
            table_name = config['table_name']
            id_column = config['id_column']
            derived_table = config['derived_table']
            
            # 读取历史数据
            conditions = {id_column: entity_id}
            df = self.reader.read_historical_data(
                table_name=table_name,
                conditions=conditions,
                start_date=start_date,
                end_date=end_date,
                date_col_name="日期"
            )
            
            if df.empty:
                logger.warning(f"未找到{entity_type} {entity_id}的历史数据")
                return
            
            # 如果是股票，还需要读取技术指标数据
            if entity_type == 'stock':
                tech_df = self.reader.read_technical_indicators(
                    stock_code=entity_id,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if not tech_df.empty:
                    # 合并历史数据和技术指标数据
                    df = pd.merge(df, tech_df, on=['日期', '股票代码'], how='left')
            
            # 计算衍生指标
            result_df = self._calculate_derived_indicators(df, entity_type)
            
            if result_df.empty:
                logger.warning(f"计算{entity_type} {entity_id}的衍生指标结果为空")
                return
            
            # 添加实体ID列和更新时间列
            result_df[id_column] = entity_id
            result_df['updated_at'] = datetime.now()
            
            # 存储结果
            if not self.dry_run:
                self._store_derived_indicators(result_df, derived_table, [id_column, '日期'])
                logger.info(f"存储{entity_type} {entity_id}的衍生指标完成，共{len(result_df)}条记录")
            else:
                logger.info(f"[Dry Run] 计算{entity_type} {entity_id}的衍生指标完成，共{len(result_df)}条记录")
                
        except Exception as e:
            logger.error(f"处理{entity_type} {entity_id}失败: {e}")
    
    def _calculate_derived_indicators(self, df, entity_type):
        """计算衍生指标
        
        Args:
            df (pandas.DataFrame): 输入数据
            entity_type (str): 实体类型 ('stock', 'industry', 'index')
            
        Returns:
            pandas.DataFrame: 计算结果
        """
        if df.empty:
            return pd.DataFrame()
        
        # 获取该实体类型的所有指标计算函数
        indicators = self.entity_config[entity_type]['indicators']
        
        # 复制一份数据，避免修改原始数据
        result_df = df[['日期']].copy()
        
        # 计算每个衍生指标
        for indicator_name, indicator_func in indicators.items():
            try:
                # 调用指标计算函数
                indicator_result = indicator_func(df)
                
                # 如果结果是DataFrame，合并到结果中
                if isinstance(indicator_result, pd.DataFrame):
                    result_df = pd.merge(result_df, indicator_result, on='日期', how='left')
                # 如果结果是Series，添加为新列
                elif isinstance(indicator_result, pd.Series):
                    result_df[indicator_name] = indicator_result
                # 如果结果是元组，解包并添加为多个列
                elif isinstance(indicator_result, tuple) and len(indicator_result) == 2:
                    column_names, values = indicator_result
                    for col, val in zip(column_names, values):
                        result_df[col] = val
            except Exception as e:
                logger.error(f"计算指标 {indicator_name} 失败: {e}")
        
        return result_df
    
    def _store_derived_indicators(self, df, table_name, primary_keys):
        """存储衍生指标到数据库
        
        Args:
            df (pandas.DataFrame): 衍生指标数据
            table_name (str): 表名
            primary_keys (list): 主键列名列表
        """
        try:
            # 使用UPSERT语法插入或更新数据
            self.pg_manager.upsert_from_df(
                df=df,
                table_name=table_name,
                primary_keys=primary_keys
            )
        except Exception as e:
            logger.error(f"存储衍生指标到{table_name}失败: {e}")
            raise


# 以下是内置的衍生指标计算函数
# 使用装饰器标记指标元数据，便于动态注册和管理

@indicator(name="golden_cross", description="短期均线从下方穿过长期均线形成的买入信号", 
          required_columns=["SMA5", "SMA20"])
def calculate_example_derived_indicator(df):
    """计算示例衍生指标：金叉信号
    
    当短期均线（如SMA5）从下方穿过长期均线（如SMA20）时，形成金叉信号。
    
    Args:
        df (pandas.DataFrame): 输入数据，需要包含SMA5和SMA20列
        
    Returns:
        pandas.DataFrame: 包含金叉信号的DataFrame
    """
    if df.empty or 'SMA5' not in df.columns or 'SMA20' not in df.columns:
        return df
    
    # 确保数据按日期排序
    df = df.sort_values('日期')
    
    # 创建结果DataFrame
    result = pd.DataFrame({'日期': df['日期']})
    
    # 计算金叉信号
    # 金叉信号：当前SMA5 > SMA20，且前一天SMA5 <= SMA20
    result['golden_cross'] = 0
    for i in range(1, len(df)):
        if (df['SMA5'].iloc[i] > df['SMA20'].iloc[i] and 
            df['SMA5'].iloc[i-1] <= df['SMA20'].iloc[i-1]):
            result['golden_cross'].iloc[i] = 1
    
    return result

@indicator(name="death_cross", description="短期均线从上方穿过长期均线形成的卖出信号", 
          required_columns=["SMA5", "SMA20"])
def calculate_death_cross(df):
    """计算死叉信号
    
    当短期均线（如SMA5）从上方穿过长期均线（如SMA20）时，形成死叉信号。
    
    Args:
        df (pandas.DataFrame): 输入数据，需要包含SMA5和SMA20列
        
    Returns:
        pandas.DataFrame: 包含死叉信号的DataFrame
    """
    if df.empty or 'SMA5' not in df.columns or 'SMA20' not in df.columns:
        return df
    
    # 确保数据按日期排序
    df = df.sort_values('日期')
    
    # 创建结果DataFrame
    result = pd.DataFrame({'日期': df['日期']})
    
    # 计算死叉信号
    # 死叉信号：当前SMA5 < SMA20，且前一天SMA5 >= SMA20
    result['death_cross'] = 0
    for i in range(1, len(df)):
        if (df['SMA5'].iloc[i] < df['SMA20'].iloc[i] and 
            df['SMA5'].iloc[i-1] >= df['SMA20'].iloc[i-1]):
            result['death_cross'].iloc[i] = 1
    
    return result

@indicator(name="rsi_signals", description="RSI超买超卖信号", 
          required_columns=["RSI14"])
def calculate_rsi_signals(df):
    """计算RSI超买超卖信号
    
    RSI > 70 为超买，RSI < 30 为超卖
    
    Args:
        df (pandas.DataFrame): 输入数据，需要包含RSI14列
        
    Returns:
        pandas.DataFrame: 包含RSI信号的DataFrame
    """
    if df.empty or 'RSI14' not in df.columns:
        return df
    
    # 创建结果DataFrame
    result = pd.DataFrame({'日期': df['日期']})
    
    # 计算RSI超买信号
    result['rsi_overbought'] = 0
    result.loc[df['RSI14'] > 70, 'rsi_overbought'] = 1
    
    # 计算RSI超卖信号
    result['rsi_oversold'] = 0
    result.loc[df['RSI14'] < 30, 'rsi_oversold'] = 1
    
    return result

@indicator(name="macd_signals", description="MACD金叉死叉信号", 
          required_columns=["DIFF", "DEA"])
def calculate_macd_signals(df):
    """计算MACD金叉死叉信号
    
    DIFF从下方穿过DEA形成金叉，DIFF从上方穿过DEA形成死叉
    
    Args:
        df (pandas.DataFrame): 输入数据，需要包含DIFF和DEA列
        
    Returns:
        pandas.DataFrame: 包含MACD信号的DataFrame
    """
    if df.empty or 'DIFF' not in df.columns or 'DEA' not in df.columns:
        return df
    
    # 确保数据按日期排序
    df = df.sort_values('日期')
    
    # 创建结果DataFrame
    result = pd.DataFrame({'日期': df['日期']})
    
    # 计算MACD金叉信号
    result['macd_golden_cross'] = 0
    # 计算MACD死叉信号
    result['macd_death_cross'] = 0
    
    for i in range(1, len(df)):
        # MACD金叉：当前DIFF > DEA，且前一天DIFF <= DEA
        if (df['DIFF'].iloc[i] > df['DEA'].iloc[i] and 
            df['DIFF'].iloc[i-1] <= df['DEA'].iloc[i-1]):
            result['macd_golden_cross'].iloc[i] = 1
        
        # MACD死叉：当前DIFF < DEA，且前一天DIFF >= DEA
        if (df['DIFF'].iloc[i] < df['DEA'].iloc[i] and 
            df['DIFF'].iloc[i-1] >= df['DEA'].iloc[i-1]):
            result['macd_death_cross'].iloc[i] = 1
    
    return result

@indicator(name="industry_strength", description="行业强度指标", 
          entity_types=["industry"], required_columns=["收盘", "SMA20"])
def calculate_industry_strength(df):
    """计算行业强度指标
    
    行业强度 = (当前收盘价 - 20日均线) / 20日均线 * 100
    
    Args:
        df (pandas.DataFrame): 输入数据，需要包含收盘价和SMA20列
        
    Returns:
        pandas.DataFrame: 包含行业强度的DataFrame
    """
    if df.empty or '收盘' not in df.columns or 'SMA20' not in df.columns:
        return df
    
    # 创建结果DataFrame
    result = pd.DataFrame({'日期': df['日期']})
    
    # 计算行业强度
    result['industry_strength'] = (df['收盘'] - df['SMA20']) / df['SMA20'] * 100
    
    return result

@indicator(name="market_breadth", description="市场宽度指标", 
          entity_types=["index"], required_columns=[])
def calculate_market_breadth(df):
    """计算市场宽度指标
    
    市场宽度是一个虚拟指标，在实际应用中需要从其他数据源获取
    这里仅作为示例，返回一个随机值
    
    Args:
        df (pandas.DataFrame): 输入数据
        
    Returns:
        pandas.DataFrame: 包含市场宽度的DataFrame
    """
    if df.empty:
        return df
    
    # 创建结果DataFrame
    result = pd.DataFrame({'日期': df['日期']})
    
    # 生成随机市场宽度值（实际应用中应该从其他数据源获取）
    result['market_breadth'] = np.random.uniform(0, 1, size=len(df))
    
    return result


# 如果直接运行此脚本，则执行示例代码
if __name__ == "__main__":
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)
    
    # 创建计算器实例（使用dry_run模式，不写入数据库）
    calculator = DerivedIndicatorCalculator(dry_run=True)
    
    # 处理单个股票
    calculator.process_entity('stock', '000001', '2023-01-01', '2023-01-31')
    
    # 处理单个行业
    calculator.process_entity('industry', '计算机', '2023-01-01', '2023-01-31')
    
    # 处理单个指数
    calculator.process_entity('index', '000300', '2023-01-01', '2023-01-31')
    
    logger.info("示例运行完成")