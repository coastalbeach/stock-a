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
from db.enhanced_postgresql_manager import EnhancedPostgreSQLManager
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
        self.pg_manager = PostgreSQLManager()
        
        # 初始化表结构管理器
        if not dry_run:
            try:
                from db.table_structure_manager import TableStructureManager
                self.table_manager = TableStructureManager(db_manager=self.pg_manager)
            except ImportError as e:
                logger.warning(f"无法导入TableStructureManager: {e}")
                self.table_manager = None
        else:
            self.table_manager = None
        
        # 初始化数据读取器
        self.reader = EnhancedPostgreSQLManager()
        
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
            
            # 使用表结构管理器检查和修复表结构
            if hasattr(self, 'table_manager') and self.table_manager and not self.dry_run:
                try:
                    logger.info(f"检查表 {table_name} 结构并添加缺失的指标列")
                    check_result = self.table_manager.check_table_structure(table_name)
                    if check_result['exists'] and not check_result['complete']:
                        fix_result = self.table_manager.fix_table_structure(table_name)
                        if fix_result['success']:
                            logger.info(f"表 {table_name} 结构修复成功，添加了 {len(fix_result['added_columns'])} 个列")
                        else:
                            logger.error(f"表 {table_name} 结构修复失败: {fix_result.get('message', '')}")
                except Exception as e:
                    logger.error(f"检查和修复表结构失败: {e}")
        except Exception as e:
            logger.error(f"创建{table_name}表失败: {e}")
            raise
    
    def run(self, data_types=None, entity_ids_map=None, specific_entities=None):
        """运行衍生指标计算
        
        Args:
            data_types (list, optional): 要处理的数据类型列表，可以是 'stock', 'industry', 'index'。默认为 None，表示处理所有类型。
            entity_ids_map (dict, optional): 实体ID映射，格式为 {data_type: [entity_ids]}。默认为 None。
            specific_entities (list, optional): 特定实体列表，格式为 [(data_type, entity_id)]。默认为 None。
        """
        # 检查表结构管理器是否已初始化
        if not self.dry_run and self.table_manager:
            try:
                # 检查并修复表结构
                for data_type in (data_types or ['stock', 'industry', 'index']):
                    table_name = self.entity_config[data_type]['derived_table']
                    check_result = self.table_manager.check_table_structure(table_name)
                    
                    if not check_result['complete'] and check_result['exists']:
                        logger.info(f"表 {table_name} 结构不完整，尝试修复...")
                        fix_result = self.table_manager.fix_table_structure(table_name)
                        if fix_result['success']:
                            logger.info(f"成功修复表 {table_name} 结构，添加了 {len(fix_result['added_columns'])} 个列")
                        else:
                            logger.warning(f"修复表 {table_name} 结构失败: {fix_result['message']}")
            except Exception as e:
                logger.error(f"检查表结构失败: {e}")
        
        # 确定要处理的数据类型
        if data_types is None:
            data_types = list(self.entity_config.keys())
        else:
            # 确保所有指定的数据类型都是有效的
            for data_type in data_types:
                if data_type not in self.entity_config:
                    raise ValueError(f"无效的数据类型: {data_type}")
        
        # 初始化衍生指标表
        self._init_derived_indicator_tables()
        
        # 检查并修复表结构，确保所有配置的指标列都存在
        if not self.dry_run:
            try:
                for data_type in data_types:
                    table_name = self.entity_config[data_type]['derived_table']
                    logger.info(f"检查表 {table_name} 结构并添加缺失的指标列")
                    
                    # 获取该实体类型的所有指标
                    common_indicators = self.indicator_loader.config.get('common_indicators', {})
                    entity_indicators = self.indicator_loader.config.get(f"{data_type}_indicators", {})
                    all_indicators = {**common_indicators, **entity_indicators}
                    
                    # 为每个指标准备配置
                    indicators_config = []
                    for ind_name, ind_config in all_indicators.items():
                        indicators_config.append({
                            'name': ind_name,
                            'type': ind_config.get('type', 'FLOAT'),
                            'table': table_name
                        })
                    
                    # 添加指标列到表结构
                    if indicators_config:
                        logger.info(f"检查并添加指标列到表 {table_name}")
                        # 将列表转换为字典格式
                        indicators_dict = {}
                        for indicator in indicators_config:
                            indicators_dict[indicator['name']] = {
                                "类型": indicator['type'],
                                "表": [indicator['table']]
                            }
                        result = self.table_manager.add_indicator_columns(indicators_dict)
                        if result.get('成功', 0) > 0:
                            logger.info(f"成功添加 {result.get('成功', 0)} 个新列到表 {table_name}")
                        else:
                            logger.warning(f"添加列到表 {table_name} 失败: {result.get('message', '')}")
            except Exception as e:
                logger.error(f"检查和修复表结构失败: {e}")
        
        # 处理每种数据类型
        for data_type in data_types:
            # 获取该类型的所有实体ID
            if entity_ids_map and data_type in entity_ids_map:
                entity_ids = entity_ids_map[data_type]
            else:
                entity_ids = self._get_all_entity_ids(data_type)
            
            # 处理所有实体
            self._process_all_entities(data_type, entity_ids, specific_entities)
    
    def _get_all_entity_ids(self, data_type):
        """获取指定类型的所有实体ID
        
        Args:
            data_type (str): 实体类型 ('stock', 'industry', 'index')
            
        Returns:
            list: 实体ID列表
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
                return []
            
            entity_ids = df[id_column].tolist()
            logger.info(f"找到{len(entity_ids)}个{data_type}实体")
            return entity_ids
                
        except Exception as e:
            logger.error(f"查询{data_type}实体列表失败: {e}")
            return []
    
    def _process_all_entities(self, data_type, entity_ids, specific_entities=None):
        """处理指定类型的所有实体
        
        Args:
            data_type (str): 实体类型 ('stock', 'industry', 'index')
            entity_ids (list): 实体ID列表
            specific_entities (dict, optional): 包含特定实体处理参数的字典
        """
        # 获取当前日期作为默认结束日期
        default_end_date = datetime.now().strftime('%Y-%m-%d')
        # 默认处理最近一年的数据
        default_start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        # 处理每个实体
        for entity_id in entity_ids:
            # 检查是否有特定的日期范围设置
            start_date = default_start_date
            end_date = default_end_date
            
            if specific_entities and data_type in specific_entities and entity_id in specific_entities[data_type]:
                entity_config = specific_entities[data_type][entity_id]
                start_date = entity_config.get('start_date', default_start_date)
                end_date = entity_config.get('end_date', default_end_date)
            
            self.process_entity(data_type, entity_id, start_date, end_date)
    
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
                end_date=end_date
            )
            
            if df.empty:
                logger.warning(f"未找到{entity_type} {entity_id}的历史数据")
                return
            
            logger.info(f"读取到{entity_type} {entity_id}的历史数据 {len(df)} 条记录")
            
            # 如果是股票，还需要读取技术指标数据
            if entity_type == 'stock':
                tech_df = self.reader.read_technical_indicators(
                    stock_code=entity_id,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if tech_df.empty:
                    logger.warning(f"未找到{entity_type} {entity_id}的技术指标数据，无法计算衍生指标")
                    return
                
                logger.info(f"读取到{entity_type} {entity_id}的技术指标数据 {len(tech_df)} 条记录")
                
                # 检查必需的技术指标列是否存在
                required_columns = ['SMA5', 'SMA20', 'RSI14', 'DIFF', 'DEA']
                missing_columns = [col for col in required_columns if col not in tech_df.columns]
                if missing_columns:
                    logger.warning(f"{entity_type} {entity_id}缺少必需的技术指标列: {missing_columns}")
                
                # 合并历史数据和技术指标数据
                df = pd.merge(df, tech_df, on=['日期', '股票代码'], how='left')
                logger.info(f"合并后数据 {len(df)} 条记录")
                
                # 检查合并后的数据质量
                null_counts = df[required_columns].isnull().sum()
                for col, null_count in null_counts.items():
                    if null_count > 0:
                        logger.warning(f"技术指标 {col} 有 {null_count} 个空值")
            
            # 计算衍生指标
            result_df = self._calculate_derived_indicators(df, entity_type)
            
            if result_df.empty:
                logger.warning(f"计算{entity_type} {entity_id}的衍生指标结果为空")
                return
            
            # 检查计算结果的数据质量
            indicator_columns = [col for col in result_df.columns if col not in ['日期', id_column, 'updated_at']]
            for col in indicator_columns:
                if col in result_df.columns:
                    zero_count = (result_df[col] == 0).sum()
                    null_count = result_df[col].isnull().sum()
                    total_count = len(result_df)
                    logger.info(f"指标 {col}: 总数={total_count}, 零值={zero_count}, 空值={null_count}")
            
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
            import traceback
            logger.error(traceback.format_exc())
    
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
        
        # 获取内置的衍生指标计算函数
        builtin_indicators = {
            'golden_cross': calculate_example_derived_indicator,
            'death_cross': calculate_death_cross,
            'rsi_signals': calculate_rsi_signals,
            'macd_signals': calculate_macd_signals,
            'industry_strength': calculate_industry_strength,
            'market_breadth': calculate_market_breadth
        }
        
        # 计算每个衍生指标
        for indicator_name in ['golden_cross', 'death_cross', 'rsi_signals', 'macd_signals']:
            if indicator_name in builtin_indicators:
                try:
                    # 调用指标计算函数
                    indicator_func = builtin_indicators[indicator_name]
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
        
        # 根据实体类型计算特有指标
        if entity_type == 'industry' and 'industry_strength' in builtin_indicators:
            try:
                indicator_result = builtin_indicators['industry_strength'](df)
                if isinstance(indicator_result, pd.DataFrame):
                    result_df = pd.merge(result_df, indicator_result, on='日期', how='left')
            except Exception as e:
                logger.error(f"计算行业强度指标失败: {e}")
        
        if entity_type == 'index' and 'market_breadth' in builtin_indicators:
            try:
                indicator_result = builtin_indicators['market_breadth'](df)
                if isinstance(indicator_result, pd.DataFrame):
                    result_df = pd.merge(result_df, indicator_result, on='日期', how='left')
            except Exception as e:
                logger.error(f"计算市场宽度指标失败: {e}")
        
        return result_df
    
    def _store_derived_indicators(self, df, table_name, primary_keys):
        """存储衍生指标到数据库
        
        Args:
            df (pandas.DataFrame): 衍生指标数据
            table_name (str): 表名
            primary_keys (list): 主键列名列表
        """
        try:
            # 检查表结构，确保所有指标列都存在
            if hasattr(self, 'table_manager') and self.table_manager and not self.dry_run:
                try:
                    # 获取DataFrame中的所有指标列（排除主键列）
                    indicator_columns = [col for col in df.columns if col not in primary_keys and col != '日期']
                    
                    # 为每个指标列准备配置
                    indicators_config = []
                    for col in indicator_columns:
                        # 根据列的数据类型确定SQL类型
                        dtype = df[col].dtype
                        if pd.api.types.is_integer_dtype(dtype):
                            sql_type = 'SMALLINT'
                        elif pd.api.types.is_float_dtype(dtype):
                            sql_type = 'FLOAT'
                        else:
                            sql_type = 'VARCHAR(50)'
                        
                        indicators_config.append({
                            'name': col,
                            'type': sql_type,
                            'table': table_name
                        })
                    
                    # 添加指标列到表结构
                    if indicators_config:
                        logger.info(f"检查并添加指标列到表 {table_name}")
                        # 将列表转换为字典格式
                        indicators_dict = {}
                        for indicator in indicators_config:
                            indicators_dict[indicator['name']] = {
                                "类型": indicator['type'],
                                "表": [indicator['table']]
                            }
                        result = self.table_manager.add_indicator_columns(indicators_dict)
                        if result.get('成功', 0) > 0:
                            logger.info(f"成功添加 {result.get('成功', 0)} 个新列到表 {table_name}")
                        else:
                            logger.warning(f"添加列到表 {table_name} 失败: {result.get('message', '')}")
                except Exception as e:
                    logger.error(f"检查和更新表结构失败: {e}")
            
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
    # 创建结果DataFrame
    result = pd.DataFrame({'日期': df['日期']})
    result['golden_cross'] = 0
    
    if df.empty or 'SMA5' not in df.columns or 'SMA20' not in df.columns:
        logger.warning("计算金叉信号时缺少必需的列（SMA5或SMA20），返回默认值0")
        return result
    
    # 确保数据按日期排序
    df = df.sort_values('日期')
    
    # 计算金叉信号
    # 金叉信号：当前SMA5 > SMA20，且前一天SMA5 <= SMA20
    for i in range(1, len(df)):
        if (pd.notna(df['SMA5'].iloc[i]) and pd.notna(df['SMA20'].iloc[i]) and
            pd.notna(df['SMA5'].iloc[i-1]) and pd.notna(df['SMA20'].iloc[i-1])):
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
    # 创建结果DataFrame
    result = pd.DataFrame({'日期': df['日期']})
    result['death_cross'] = 0
    
    if df.empty or 'SMA5' not in df.columns or 'SMA20' not in df.columns:
        logger.warning("计算死叉信号时缺少必需的列（SMA5或SMA20），返回默认值0")
        return result
    
    # 确保数据按日期排序
    df = df.sort_values('日期')
    
    # 计算死叉信号
    # 死叉信号：当前SMA5 < SMA20，且前一天SMA5 >= SMA20
    for i in range(1, len(df)):
        if (pd.notna(df['SMA5'].iloc[i]) and pd.notna(df['SMA20'].iloc[i]) and
            pd.notna(df['SMA5'].iloc[i-1]) and pd.notna(df['SMA20'].iloc[i-1])):
            if (df['SMA5'].iloc[i] < df['SMA20'].iloc[i] and 
                df['SMA5'].iloc[i-1] >= df['SMA20'].iloc[i-1]):
                result['death_cross'].iloc[i] = 1
    
    return result

@indicator(name="rsi_signals", description="RSI超买超卖信号", 
          required_columns=["RSI14"])
def calculate_rsi_signals(df):
    """计算RSI超买超卖信号
    
    RSI > 70为超买信号，RSI < 30为超卖信号
    
    Args:
        df (pandas.DataFrame): 输入数据，需要包含RSI14列
        
    Returns:
        pandas.DataFrame: 包含RSI信号的DataFrame
    """
    # 创建结果DataFrame
    result = pd.DataFrame({'日期': df['日期']})
    result['rsi_overbought'] = 0
    result['rsi_oversold'] = 0
    
    if df.empty or 'RSI14' not in df.columns:
        logger.warning("计算RSI信号时缺少必需的列（RSI14），返回默认值0")
        return result
    
    # 计算RSI超买信号
    result.loc[df['RSI14'] > 70, 'rsi_overbought'] = 1
    
    # 计算RSI超卖信号
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
    # 创建结果DataFrame
    result = pd.DataFrame({'日期': df['日期']})
    result['macd_golden_cross'] = 0
    result['macd_death_cross'] = 0
    
    if df.empty or 'DIFF' not in df.columns or 'DEA' not in df.columns:
        logger.warning("计算MACD信号时缺少必需的列（DIFF或DEA），返回默认值0")
        return result
    
    # 确保数据按日期排序
    df = df.sort_values('日期')
    
    for i in range(1, len(df)):
        # MACD金叉：当前DIFF > DEA，且前一天DIFF <= DEA
        if (pd.notna(df['DIFF'].iloc[i]) and pd.notna(df['DEA'].iloc[i]) and
            pd.notna(df['DIFF'].iloc[i-1]) and pd.notna(df['DEA'].iloc[i-1])):
            if (df['DIFF'].iloc[i] > df['DEA'].iloc[i] and 
                df['DIFF'].iloc[i-1] <= df['DEA'].iloc[i-1]):
                result['macd_golden_cross'].iloc[i] = 1
        
        # MACD死叉：当前DIFF < DEA，且前一天DIFF >= DEA
        if (pd.notna(df['DIFF'].iloc[i]) and pd.notna(df['DEA'].iloc[i]) and
            pd.notna(df['DIFF'].iloc[i-1]) and pd.notna(df['DEA'].iloc[i-1])):
            if (df['DIFF'].iloc[i] < df['DEA'].iloc[i] and 
                df['DIFF'].iloc[i-1] >= df['DEA'].iloc[i-1]):
                result['macd_death_cross'].iloc[i] = 1
    
    return result

@indicator(name="industry_strength", description="行业强度指标", 
          required_columns=["收盘价", "SMA20"])
def calculate_industry_strength(df):
    """计算行业强度指标
    
    行业强度 = (当前收盘价 - 20日均线) / 20日均线 * 100
    
    Args:
        df (pandas.DataFrame): 输入数据，需要包含收盘价和SMA20列
        
    Returns:
        pandas.DataFrame: 包含行业强度指标的DataFrame
    """
    # 创建结果DataFrame
    result = pd.DataFrame({'日期': df['日期']})
    result['industry_strength'] = 0.0
    
    if df.empty or '收盘价' not in df.columns or 'SMA20' not in df.columns:
        logger.warning("计算行业强度时缺少必需的列（收盘价或SMA20），返回默认值0")
        return result
    
    # 计算行业强度，避免除零错误
    mask = (pd.notna(df['收盘价']) & pd.notna(df['SMA20']) & (df['SMA20'] != 0))
    result.loc[mask, 'industry_strength'] = ((df.loc[mask, '收盘价'] - df.loc[mask, 'SMA20']) / df.loc[mask, 'SMA20'] * 100).round(2)
    
    return result

@indicator(name="market_breadth", description="市场宽度指标", 
          entity_types=["index"], required_columns=[])
def calculate_market_breadth(df):
    """计算市场宽度指标（示例）
    
    这是一个示例函数，实际应该根据具体需求实现
    
    Args:
        df (pandas.DataFrame): 输入数据
        
    Returns:
        pandas.DataFrame: 包含市场宽度的DataFrame
    """
    # 创建结果DataFrame
    result = pd.DataFrame({'日期': df['日期']})
    result['market_breadth'] = 0.0
    
    if df.empty:
        logger.warning("计算市场宽度时数据为空，返回默认值0")
        return result
    
    # 示例：基于成交量的简单市场宽度计算
    if '成交量' in df.columns and pd.notna(df['成交量']).any():
        # 计算成交量的移动平均作为市场宽度的基础
        volume_ma = df['成交量'].rolling(window=5, min_periods=1).mean()
        result['market_breadth'] = ((df['成交量'] - volume_ma) / volume_ma * 100).fillna(0).round(2)
    else:
        logger.warning("计算市场宽度时缺少成交量数据，使用默认值0")
    
    return result


def main():
    """主函数：衍生指标计算器的命令行入口
    
    支持多种运行模式：
    1. 批量处理所有实体的衍生指标
    2. 处理特定类型的实体（股票、行业、指数）
    3. 处理特定的实体ID
    4. 指定日期范围进行处理
    5. 干运行模式（不写入数据库）
    """
    import argparse
    from datetime import datetime, timedelta
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        description='衍生指标计算器 - 计算股票、行业、指数的衍生指标',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python derived_indicators.py                                    # 处理所有实体的衍生指标
  python derived_indicators.py --types stock                     # 只处理股票
  python derived_indicators.py --types stock industry            # 处理股票和行业
  python derived_indicators.py --entity-id stock:000001          # 处理特定股票
  python derived_indicators.py --entity-id stock:000001,000002   # 处理多个股票
  python derived_indicators.py --start-date 2023-01-01 --end-date 2023-12-31  # 指定日期范围
  python derived_indicators.py --dry-run                         # 干运行模式（不写入数据库）
  python derived_indicators.py --log-level DEBUG                 # 设置日志级别
        """
    )
    
    # 添加命令行参数
    parser.add_argument(
        '--types', 
        nargs='+', 
        choices=['stock', 'industry', 'index'],
        help='指定要处理的实体类型（可多选）'
    )
    
    parser.add_argument(
        '--entity-id',
        type=str,
        help='指定要处理的实体ID，格式：type:id 或 type:id1,id2,id3。例如：stock:000001 或 stock:000001,000002'
    )
    
    parser.add_argument(
        '--start-date',
        type=str,
        help='开始日期，格式：YYYY-MM-DD（默认为30天前）'
    )
    
    parser.add_argument(
        '--end-date',
        type=str,
        help='结束日期，格式：YYYY-MM-DD（默认为今天）'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='干运行模式，不写入数据库，只显示计算结果'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='设置日志级别（默认：INFO）'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='指定数据库配置文件路径'
    )
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 设置日志级别
    log_level = getattr(logging, args.log_level.upper())
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    logger.info("="*60)
    logger.info("衍生指标计算器启动")
    logger.info("="*60)
    
    try:
        # 加载数据库配置
        db_config = None
        if args.config:
            try:
                import yaml
                with open(args.config, 'r', encoding='utf-8') as f:
                    db_config = yaml.safe_load(f)
                logger.info(f"使用配置文件: {args.config}")
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
                return 1
        
        # 创建计算器实例
        calculator = DerivedIndicatorCalculator(db_config=db_config, dry_run=args.dry_run)
        
        if args.dry_run:
            logger.info("运行模式: 干运行（不写入数据库）")
        else:
            logger.info("运行模式: 正常模式（写入数据库）")
        
        # 设置日期范围
        if args.end_date:
            try:
                end_date = datetime.strptime(args.end_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            except ValueError:
                logger.error("结束日期格式错误，请使用 YYYY-MM-DD 格式")
                return 1
        else:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        if args.start_date:
            try:
                start_date = datetime.strptime(args.start_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            except ValueError:
                logger.error("开始日期格式错误，请使用 YYYY-MM-DD 格式")
                return 1
        else:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        logger.info(f"处理日期范围: {start_date} 到 {end_date}")
        
        # 处理特定实体ID
        if args.entity_id:
            try:
                # 解析实体ID参数
                if ':' not in args.entity_id:
                    logger.error("实体ID格式错误，请使用 type:id 格式，例如：stock:000001")
                    return 1
                
                entity_type, entity_ids_str = args.entity_id.split(':', 1)
                entity_ids = [eid.strip() for eid in entity_ids_str.split(',')]
                
                if entity_type not in ['stock', 'industry', 'index']:
                    logger.error(f"无效的实体类型: {entity_type}，支持的类型：stock, industry, index")
                    return 1
                
                logger.info(f"处理特定{entity_type}实体: {entity_ids}")
                
                # 处理每个指定的实体
                for entity_id in entity_ids:
                    calculator.process_entity(entity_type, entity_id, start_date, end_date)
                
            except Exception as e:
                logger.error(f"处理特定实体时发生错误: {e}")
                import traceback
                traceback.print_exc()
                return 1
        
        # 批量处理模式
        else:
            try:
                # 确定要处理的数据类型
                data_types = args.types if args.types else ['stock', 'industry', 'index']
                logger.info(f"处理数据类型: {data_types}")
                
                # 运行批量处理
                calculator.run(data_types=data_types)
                
            except Exception as e:
                logger.error(f"批量处理时发生错误: {e}")
                import traceback
                traceback.print_exc()
                return 1
        
        logger.info("="*60)
        logger.info("衍生指标计算完成")
        logger.info("="*60)
        return 0
        
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        return 1
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    """脚本入口点"""
    import sys
    sys.exit(main())