# -*- coding: utf-8 -*-

"""
技术指标计算模块

读取股票、行业、指数的历史行情数据，使用 TA-Lib 计算常用技术指标，
并将结果存储到 PostgreSQL 数据库中。

优化版本：使用多进程并行计算，提高CPU利用率。
集成表结构管理器，支持动态添加新的技术指标列。
"""

import os
import sys
import pandas as pd
import talib
import psycopg2
import psycopg2.extras
import yaml
from pathlib import Path
import argparse
from tqdm import tqdm
import numpy as np
import logging
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import time
from functools import lru_cache, wraps
import functools
import psutil

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 性能监控装饰器
def performance_monitor(func):
    """装饰器：监控函数执行时间和资源使用情况"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 记录开始时间和资源使用
        start_time = time.time()
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        start_cpu = psutil.cpu_percent(interval=0.1)
        
        # 执行原函数
        result = func(*args, **kwargs)
        
        # 记录结束时间和资源使用
        end_time = time.time()
        end_memory = process.memory_info().rss / 1024 / 1024  # MB
        end_cpu = psutil.cpu_percent(interval=0.1)
        
        # 计算差异
        elapsed_time = end_time - start_time
        memory_diff = end_memory - start_memory
        
        # 记录性能数据
        logger.debug(f"性能监控 - {func.__name__}: 耗时={elapsed_time:.2f}秒, "
                    f"内存变化={memory_diff:.2f}MB, CPU使用={end_cpu}%")
        
        return result
    return wrapper

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 尝试导入自定义的 PostgreSQLManager，如果失败则使用简化的连接
# 定义全局变量
PostgreSQLManager = None
try:
    from db.postgresql_manager import PostgreSQLManager
    #logger.info("使用项目 PostgreSQLManager")
except ImportError:
    logger.warning("未找到项目 PostgreSQLManager，将使用简化的数据库连接方法。")

# 导入表结构管理器
try:
    from db.table_structure_manager import TableStructureManager
    #logger.info("导入表结构管理器成功")
except ImportError:
    logger.warning("未找到表结构管理器，将无法自动添加新的技术指标列。")

def load_db_config():
    """加载数据库连接配置"""
    config_path = Path(project_root) / 'config' / 'connection.yaml'
    if not config_path.exists():
        logger.error(f"错误：数据库配置文件 {config_path} 未找到。")
        raise FileNotFoundError(f"数据库配置文件 {config_path} 未找到。")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    db_params = config.get('postgresql')
    if not db_params:
        logger.error(f"配置文件 {config_path} 中未找到 'postgresql' 配置部分。")
        raise ValueError(f"配置文件 {config_path} 中未找到 'postgresql' 配置部分。")
    return db_params

class TechnicalIndicatorCalculator:
    """技术指标计算和存储类"""

    def __init__(self, db_config, dry_run=False, max_workers=None, batch_size=50, cache_size=128, max_lookback_period=100):
        """初始化计算器

        Args:
            db_config (dict): 数据库连接配置
            dry_run (bool): 如果为True，则不执行数据库写入操作
            max_workers (int, optional): 最大工作进程数，默认为CPU核心数
            batch_size (int, optional): 数据批处理大小，默认为50
            cache_size (int, optional): 缓存大小，默认为128
            max_lookback_period (int, optional): 计算指标所需的最大回溯期，默认为100天
        """
        self.db_config = db_config
        self.dry_run = dry_run
        self.conn = None
        self.cursor = None
        self.pg_manager = None
        self.table_manager = None
        
        # 性能优化参数
        self.batch_size = batch_size
        self.max_workers = max_workers if max_workers else max(1, mp.cpu_count() - 1)
        self.cache_size = cache_size
        self.max_lookback_period = max_lookback_period
        
        # 显示系统资源信息
        cpu_count = psutil.cpu_count(logical=True)
        physical_cores = psutil.cpu_count(logical=False)
        memory = psutil.virtual_memory()
        logger.info(f"系统资源信息: CPU总核心数={cpu_count}, 物理核心数={physical_cores}, ")
        logger.info(f"内存总量={memory.total/1024/1024/1024:.2f}GB, 可用内存={memory.available/1024/1024/1024:.2f}GB")
        logger.info(f"将使用 {self.max_workers} 个工作进程进行并行计算")

        if PostgreSQLManager:
            try:
                self.pg_manager = PostgreSQLManager()
                logger.info("PostgreSQLManager 初始化成功。")
            except Exception as e:
                logger.error(f"PostgreSQLManager 初始化失败: {e}。将回退到简化连接。")
                # 不要修改全局变量，只需将实例变量设为None
                self.pg_manager = None
                self._connect_db()
        else:
            self._connect_db()
            
        # 初始化表结构管理器
        try:
            if 'TableStructureManager' in globals():
                self.table_manager = TableStructureManager(db_manager=self.pg_manager)
                logger.info("表结构管理器初始化成功。")
        except Exception as e:
            logger.warning(f"表结构管理器初始化失败: {e}。将无法自动添加新的技术指标列。")
            self.table_manager = None

        self._create_indicator_tables()

    def _connect_db(self):
        """连接到PostgreSQL数据库 (简化版，如果PostgreSQLManager不可用)"""
        if self.conn is None or self.conn.closed != 0:
            try:
                # 只使用标准的PostgreSQL连接参数
                standard_params = {
                    'host': self.db_config['host'],
                    'port': self.db_config['port'],
                    'database': self.db_config['database'],
                    'user': self.db_config['user'],
                    'password': self.db_config['password']
                }
                self.conn = psycopg2.connect(**standard_params)
                self.cursor = self.conn.cursor()
                logger.info("数据库连接成功")
            except Exception as e:
                logger.error(f"数据库连接失败: {e}")
                raise

    def _close_db(self):
        """关闭数据库连接"""
        # 关闭表结构管理器
        if self.table_manager:
            if hasattr(self.table_manager, 'close') and callable(self.table_manager.close):
                self.table_manager.close()
                logger.info("表结构管理器连接已关闭。")
            else:
                logger.warning("表结构管理器没有可调用的 close 方法。")
        
        # 关闭数据库管理器
        if self.pg_manager:
            if hasattr(self.pg_manager, 'close') and callable(self.pg_manager.close):
                self.pg_manager.close()
                logger.info("PostgreSQLManager 连接已关闭。")
            else:
                logger.warning("PostgreSQLManager 没有可调用的 close 方法。")
        elif self.conn:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
            logger.info("数据库连接已关闭")

    def _execute_query(self, query, params=None, fetch=False):
        """执行SQL查询"""
        if self.pg_manager:
            try:
                if fetch == 'one':
                    return self.pg_manager.query_one(query, params)
                elif fetch:
                    return self.pg_manager.query(query, params)
                else:
                    return self.pg_manager.execute(query, params)
            except Exception as e:
                logger.error(f"PostgreSQLManager 执行查询失败: {query}, {params}, {e}")
                raise
        else:
            self._connect_db()
            try:
                self.cursor.execute(query, params)
                if fetch == 'one':
                    return self.cursor.fetchone()
                elif fetch:
                    return self.cursor.fetchall()
                else:
                    self.conn.commit()
                    return self.cursor.rowcount
            except Exception as e:
                logger.error(f"执行查询失败 (简化版): {query}, {params}, {e}")
                if self.conn:
                    self.conn.rollback()
                raise

    def _create_indicator_tables(self):
        """创建存储技术指标的表 (如果不存在)，并使用表结构管理器检查和修复表结构"""
        # 首先使用原始方法创建基本表结构
        table_definitions = {
            "股票技术指标": """
                CREATE TABLE IF NOT EXISTS public."股票技术指标"
                (
                    "股票代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
                    "日期" date NOT NULL,
                    "SMA5" double precision, "SMA10" double precision, "SMA20" double precision, "SMA60" double precision,
                    "EMA12" double precision, "EMA26" double precision,
                    "DIF" double precision, "DEA" double precision, "MACD_hist" double precision,
                    "RSI6" double precision, "RSI12" double precision, "RSI24" double precision,
                    "BBANDS_UPPER" double precision, "BBANDS_MIDDLE" double precision, "BBANDS_LOWER" double precision,
                    "KDJ_K" double precision, "KDJ_D" double precision, "KDJ_J" double precision,
                    "VOL_MA5" double precision, "VOL_MA10" double precision,
                    "WR14" double precision, "CCI14" double precision,
                    "PDI14" double precision, "MDI14" double precision, "ADX14" double precision,
                    "ROC6" double precision, "ROC12" double precision,
                    "BIAS6" double precision, "BIAS12" double precision, "BIAS24" double precision,
                    "OBV" double precision, "OBV_MA5" double precision, "OBV_MA10" double precision,
                    CONSTRAINT "股票技术指标_pkey" PRIMARY KEY ("股票代码", "日期"),
                    CONSTRAINT "股票技术指标_fkey" FOREIGN KEY ("股票代码", "日期")
                        REFERENCES public."股票历史行情_后复权" ("股票代码", "日期") MATCH SIMPLE
                        ON UPDATE NO ACTION ON DELETE CASCADE
                )
                PARTITION BY HASH ("股票代码");
            """,
            "行业技术指标": """
                CREATE TABLE IF NOT EXISTS public."行业技术指标"
                (
                    "行业名称" character varying(100) COLLATE pg_catalog."default" NOT NULL,
                    "日期" date NOT NULL,
                    "SMA5" double precision, "SMA10" double precision, "SMA20" double precision, "SMA60" double precision,
                    "EMA12" double precision, "EMA26" double precision,
                    "DIF" double precision, "DEA" double precision, "MACD_hist" double precision,
                    "RSI6" double precision, "RSI12" double precision, "RSI24" double precision,
                    "BBANDS_UPPER" double precision, "BBANDS_MIDDLE" double precision, "BBANDS_LOWER" double precision,
                    "KDJ_K" double precision, "KDJ_D" double precision, "KDJ_J" double precision,
                    "VOL_MA5" double precision, "VOL_MA10" double precision,
                    "WR14" double precision, "CCI14" double precision,
                    "PDI14" double precision, "MDI14" double precision, "ADX14" double precision,
                    "ROC6" double precision, "ROC12" double precision,
                    "BIAS6" double precision, "BIAS12" double precision, "BIAS24" double precision,
                    "OBV" double precision, "OBV_MA5" double precision, "OBV_MA10" double precision,
                    CONSTRAINT "行业技术指标_pkey" PRIMARY KEY ("行业名称", "日期"),
                    CONSTRAINT "行业技术指标_fkey" FOREIGN KEY ("行业名称", "日期")
                        REFERENCES public."行业历史行情" ("行业名称", "日期") MATCH SIMPLE
                        ON UPDATE NO ACTION ON DELETE CASCADE
                )
            """,
            "指数技术指标": """
                CREATE TABLE IF NOT EXISTS public."指数技术指标"
                (
                    "指数代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
                    "日期" date NOT NULL,
                    "SMA5" double precision, "SMA10" double precision, "SMA20" double precision, "SMA60" double precision,
                    "EMA12" double precision, "EMA26" double precision,
                    "DIF" double precision, "DEA" double precision, "MACD_hist" double precision,
                    "RSI6" double precision, "RSI12" double precision, "RSI24" double precision,
                    "BBANDS_UPPER" double precision, "BBANDS_MIDDLE" double precision, "BBANDS_LOWER" double precision,
                    "KDJ_K" double precision, "KDJ_D" double precision, "KDJ_J" double precision,
                    "VOL_MA5" double precision, "VOL_MA10" double precision,
                    "WR14" double precision, "CCI14" double precision,
                    "PDI14" double precision, "MDI14" double precision, "ADX14" double precision,
                    "ROC6" double precision, "ROC12" double precision,
                    "BIAS6" double precision, "BIAS12" double precision, "BIAS24" double precision,
                    "OBV" double precision, "OBV_MA5" double precision, "OBV_MA10" double precision,
                    CONSTRAINT "指数技术指标_pkey" PRIMARY KEY ("指数代码", "日期"),
                    CONSTRAINT "指数技术指标_fkey" FOREIGN KEY ("指数代码", "日期")
                        REFERENCES public."指数历史行情" ("指数代码", "日期") MATCH SIMPLE
                        ON UPDATE NO ACTION ON DELETE CASCADE
                )
            """
        }
        
        # 首先创建基本表结构
        for table_name, ddl in table_definitions.items():
            try:
                if self.dry_run:
                    logger.info(f"[DRY RUN] Would ensure table {table_name} exists (CREATE TABLE IF NOT EXISTS)")
                    if table_name == "股票技术指标": # Specific dry-run log for partitioning
                        logger.info(f"[DRY RUN] Table {table_name} would be HASH partitioned by '股票代码'.")
                        # Add dry-run logging for partition sub-tables
                        num_partitions = 10 # Define the number of partitions
                        for i in range(num_partitions):
                            partition_table_name = f'{table_name}_p{i}'
                            logger.info(f'[DRY RUN] Would ensure partition sub-table public."{partition_table_name}" FOR VALUES WITH (MODULUS {num_partitions}, REMAINDER {i}) exists.')
                    logger.info(f"[DRY RUN] Would ensure index idx_{table_name}_日期 on '日期' for table {table_name} exists.")
                else:
                    # Execute main DDL (CREATE TABLE)
                    if self.pg_manager:
                        self.pg_manager.execute(ddl)
                    else:
                        self._connect_db()
                        self.cursor.execute(ddl)
                        self.conn.commit() # Commit DDL
                    logger.info(f"表 {table_name} DDL 检查/创建成功。")

                    # Create partition sub-tables for "股票技术指标"
                    if table_name == "股票技术指标":
                        num_partitions = 16  # Define the number of partitions
                        for i in range(num_partitions):
                            partition_table_name = f'{table_name}_p{i}'
                            # Ensure partition table names are correctly quoted if they contain special characters or are case-sensitive
                            # For simplicity, assuming standard naming that doesn't strictly require quoting here, but PostgreSQL will handle it.
                            partition_ddl = f'''
                                CREATE TABLE IF NOT EXISTS public."{partition_table_name}"
                                PARTITION OF public."{table_name}"
                                FOR VALUES WITH (MODULUS {num_partitions}, REMAINDER {i});
                            '''
                            try:
                                if self.pg_manager:
                                    self.pg_manager.execute(partition_ddl)
                                else:
                                    # self._connect_db() # Connection should be active from main DDL execution
                                    self.cursor.execute(partition_ddl)
                                    self.conn.commit() # Commit each partition creation
                                logger.info(f'分区子表 public."{partition_table_name}" 检查/创建成功。')
                            except Exception as e_part:
                                logger.error(f'创建分区子表 public."{partition_table_name}" 失败: {e_part}')
                                # Optionally, re-raise or handle as critical

                    # Create index on "日期" for all tables
                    index_ddl_date = f'CREATE INDEX IF NOT EXISTS idx_{table_name}_日期 ON public."{table_name}" ("日期");'
                    if self.pg_manager:
                        self.pg_manager.execute(index_ddl_date)
                    else:
                        # self._connect_db() # Should still be connected from DDL execution if not using pg_manager
                        self.cursor.execute(index_ddl_date)
                        self.conn.commit() # Commit index creation
                    logger.info(f"表 {table_name} 的 日期索引 idx_{table_name}_日期 检查/创建成功。")
                
                # Overall success message if not dry run
                if not self.dry_run:
                    logger.info(f"表 {table_name} 及其相关结构检查/创建成功。")

            except Exception as e:
                logger.error(f"处理表 {table_name} (创建表或索引) 失败: {e}")
                # Consider raising e if table creation is critical
        
        # 使用表结构管理器检查和修复表结构，添加新的技术指标列
        if self.table_manager and not self.dry_run:
            try:
                # 检查并修复技术指标表结构
                indicator_tables = ["股票技术指标", "行业技术指标", "指数技术指标"]
                for table_name in indicator_tables:
                    # 检查表结构
                    check_result = self.table_manager.check_table_structure(table_name)
                    if not check_result['exists'] or not check_result['structure_ok']:
                        logger.info(f"表 {table_name} 需要修复结构")
                        # 修复表结构
                        fix_result = self.table_manager.fix_table_structure(table_name)
                        if fix_result['success']:
                            logger.info(f"表 {table_name} 结构修复成功，添加了 {len(fix_result['added_columns'])} 个列")
                            # 如果有新增列，提供数据填充指导
                            if fix_result['added_columns']:
                                for column in fix_result['added_columns']:
                                    guidance = self.table_manager.get_column_data_fill_guidance(table_name, column)
                                    logger.info(f"列 {column} 添加成功，数据填充指导: {guidance}")
                        else:
                            logger.error(f"表 {table_name} 结构修复失败: {fix_result['error']}")
                
                # 检查是否需要添加海龟交易策略所需的指标列
                turtle_indicators = [
                    {"name": "ATR14", "type": "double precision", "description": "14日平均真实波幅"},
                    {"name": "ATR20", "type": "double precision", "description": "20日平均真实波幅"},
                    {"name": "HIGHEST_20", "type": "double precision", "description": "20日最高价"},
                    {"name": "HIGHEST_55", "type": "double precision", "description": "55日最高价"},
                    {"name": "LOWEST_10", "type": "double precision", "description": "10日最低价"},
                    {"name": "LOWEST_20", "type": "double precision", "description": "20日最低价"}
                ]
                
                for table_name in indicator_tables:
                    add_result = self.table_manager.add_indicator_columns(table_name, turtle_indicators)
                    if add_result['success']:
                        logger.info(f"表 {table_name} 添加海龟交易策略指标列成功: 新增 {len(add_result['added'])} 个，已存在 {len(add_result['existing'])} 个")
                    else:
                        logger.error(f"表 {table_name} 添加海龟交易策略指标列失败: {add_result['error']}")
                        
            except Exception as e:
                logger.error(f"使用表结构管理器检查和修复表结构失败: {e}")
        elif self.dry_run and self.table_manager:
            logger.info("[DRY RUN] 将使用表结构管理器检查和修复表结构，添加新的技术指标列")
        elif not self.table_manager:
            logger.warning("表结构管理器未初始化，跳过表结构检查和修复")
        else:
            logger.warning("未知原因，跳过表结构检查和修复")

    def _get_all_entity_ids_from_historical_table(self, data_type):
        """从历史行情数据表中获取所有唯一的实体ID"""
        id_column_db = ""
        table_db = ""
        if data_type == 'stock':
            id_column_db = '"股票代码"'
            table_db = 'public."股票历史行情_后复权"'
        elif data_type == 'industry':
            id_column_db = '"行业名称"'
            table_db = 'public."行业历史行情"'
        elif data_type == 'index':
            id_column_db = '"指数代码"'
            table_db = 'public."指数历史行情"'
        else:
            logger.error(f"无效的数据类型: {data_type} 用于获取实体ID")
            return []

        query = f"SELECT DISTINCT {id_column_db} FROM {table_db}"
        try:
            results = self._execute_query(query, fetch=True)
            return [row[0] for row in results] if results else []
        except Exception as e:
            logger.error(f"从 {table_db} 获取所有实体ID失败: {e}")
            return []

    def _get_entity_last_indicator_dates(self, data_type, entity_ids_to_filter=None):
        """获取指定实体或所有已计算实体的最新指标日期"""
        id_column_db = ""
        table_db = ""
        if data_type == 'stock':
            id_column_db = '"股票代码"'
            table_db = 'public."股票技术指标"'
        elif data_type == 'industry':
            id_column_db = '"行业名称"'
            table_db = 'public."行业技术指标"'
        elif data_type == 'index':
            id_column_db = '"指数代码"'
            table_db = 'public."指数技术指标"'
        else:
            logger.error(f"无效的数据类型: {data_type} 用于获取最新指标日期")
            return {}

        query = f"SELECT {id_column_db}, MAX(\"日期\") FROM {table_db}"
        params = []
        if entity_ids_to_filter:
            query += f" WHERE {id_column_db} = ANY(%s)"
            params.append(list(entity_ids_to_filter))
        query += f" GROUP BY {id_column_db}"

        last_dates = {}
        try:
            results = self._execute_query(query, tuple(params) if params else None, fetch=True)
            if results:
                for row in results:
                    last_dates[row[0]] = row[1]
        except Exception as e:
            logger.error(f"从 {table_db} 获取最新指标日期失败: {e}")
        return last_dates

    @performance_monitor
    def _fetch_historical_data(self, data_type, entity_ids=None):
        """获取历史行情数据，支持增量更新"""
        id_column_db = ""
        table_db = ""
        if data_type == 'stock':
            id_column_db = '"股票代码"'
            table_db = 'public."股票历史行情_后复权"'
        elif data_type == 'industry':
            id_column_db = '"行业名称"'
            table_db = 'public."行业历史行情"'
        elif data_type == 'index':
            id_column_db = '"指数代码"'
            table_db = 'public."指数历史行情"'
        else:
            raise ValueError(f"无效的数据类型: {data_type}")

        # 获取已计算指标的最新日期
        last_indicator_dates = self._get_entity_last_indicator_dates(data_type, entity_ids)

        # 确定需要获取数据的最早日期
        # 默认从一个非常早的日期开始，以防没有任何指标数据
        overall_min_start_date = pd.Timestamp('1990-01-01') 

        # 如果有指定实体ID，则针对这些实体确定最小开始日期
        # 否则，考虑所有实体的最新指标日期（如果适用）
        # 当前逻辑简化为：如果提供了entity_ids，则只考虑这些；否则，获取所有历史数据（除非后续优化）
        # 增量更新的核心：只获取从 (最新指标日期 - 回溯期) 之后的数据

        query_conditions = []
        params = []

        if entity_ids:
            # 为每个实体确定其特定的开始日期
            # 这里简化处理：如果一个实体没有指标，则获取其全部历史数据
            # 如果有指标，则从 (last_indicator_date - lookback_period) 开始获取
            # 为了批量查询，我们可能需要找到所有这些日期中的最早者，或者为每个实体分别查询
            # 目前，为了简化，如果提供了entity_ids，我们先不应用复杂的日期过滤，依赖后续的指标计算逻辑来处理
            # 这是一个可以进一步优化的地方：为每个entity_id动态计算start_date
            query_conditions.append(f"{id_column_db} = ANY(%s)")
            params.append(list(entity_ids))
        
        # 确定全局最小开始日期，用于获取足够的回溯数据
        # 如果 last_indicator_dates 不为空，找到所有日期中的最小值
        min_last_date_overall = None
        if last_indicator_dates:
            min_last_date_overall = min(last_indicator_dates.values()) if last_indicator_dates else None
        
        # 如果有最新的指标日期，并且我们没有指定特定的entity_ids (即全量更新时)
        # 或者即使指定了entity_ids，我们也需要一个统一的起始点来保证回溯期
        if min_last_date_overall:
            # 从 (最新指标日期 - 回溯期) 开始获取数据，以确保指标计算的连续性
            # 但如果 (最新指标日期 - 回溯期) 比 '1990-01-01' 还早，则使用 '1990-01-01'
            # 同时，数据获取的开始日期不应晚于 min_last_date_overall 本身，以防回溯期过大导致跳过新数据
            potential_start_date = min_last_date_overall - pd.Timedelta(days=self.max_lookback_period)
            # 确保开始日期不早于数据库的实际最早日期（这里用1990年作为硬编码下限）
            start_date_for_query = max(overall_min_start_date, pd.Timestamp(potential_start_date))
            # 确保获取的数据至少包含最新的指标日期之后的数据
            # 如果 start_date_for_query 晚于 min_last_date_overall，说明回溯期不足，应从 min_last_date_overall 开始
            # 或者，更简单地，如果我们要更新，至少从 min_last_date_overall 开始获取，然后向前推回溯期
            # 修正：应该是从 (min_last_date_overall - max_lookback_period) 或 (min_last_date_overall - 1 day) 中较早者开始
            # 以确保我们获取了足够的数据进行回溯计算，并且至少获取了最新指标日期之后的新数据
            # 如果实体没有历史指标，则 last_indicator_dates[entity_id] 不存在，此时应获取全部历史
            # 此处逻辑需要更精细化，针对每个entity_id
            # 简化：如果存在任何已计算的指标，则将查询的起始日期限制在 (最早的最新指标日期 - 回溯期)
            # 这样可以避免加载过多的旧数据，但可能对没有指标的实体加载过多
            # 一个更优的策略是，对有指标的实体，从 (last_date - lookback) 开始；对没有指标的实体，从头开始。
            # 这需要更复杂的查询或多次查询。
            # 当前简化：如果存在任何指标，则应用一个统一的较早的起始日期。
            if not entity_ids: # 只有在全量更新时，才根据全局最小日期调整
                query_conditions.append(f'"日期" >= %s')
                params.append(start_date_for_query.strftime('%Y-%m-%d'))
        
        query = f'SELECT {id_column_db}, "日期", "开盘", "收盘", "最高", "最低", "成交量" FROM {table_db}'
        if query_conditions:
            query += " WHERE " + " AND ".join(query_conditions)
        
        query += f" ORDER BY {id_column_db}, \"日期\" ASC"

        #logger.info(f"正在获取 {data_type} 历史数据...")
        
        df = pd.DataFrame()
        try:
            if self.pg_manager:
                df = self.pg_manager.query_df(query, tuple(params) if params else None)
            else:
                self._connect_db()
                df = pd.read_sql_query(query, self.conn, params=tuple(params) if params else None)
        except Exception as e:
            logger.error(f"从数据库获取 {data_type} 数据失败: {e}")
            return pd.DataFrame() # Return empty DataFrame on error
            
        if df is None or df.empty:
            logger.warning(f"未能从数据库获取 {data_type} 数据，或数据为空")
            return pd.DataFrame()
            
        rename_map = {'开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low', '成交量': 'volume'}
        df.rename(columns=rename_map, inplace=True)
        for col in ['open', 'close', 'high', 'low', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df['日期'] = pd.to_datetime(df['日期'])
        return df

    @staticmethod
    def _get_indicator_calculators():
        """获取所有支持的技术指标计算函数
        
        返回一个字典，键为指标名称，值为计算该指标的函数。
        这样设计可以方便地添加新的技术指标，只需在此处添加新的计算函数即可。
        """
        calculators = {}
        
        # 移动平均线类指标
        calculators['calc_sma'] = lambda data, period: talib.SMA(data, timeperiod=period) if len(data) >= period else np.nan
        calculators['calc_ema'] = lambda data, period: talib.EMA(data, timeperiod=period) if len(data) >= period else np.nan
        
        # MACD指标
        def calc_macd(data):
            if len(data) >= 26:  # MACD typically needs at least 26 periods for slow EMA
                dif, dea, hist = talib.MACD(data, fastperiod=12, slowperiod=26, signalperiod=9)
                return dif, dea, hist
            return np.nan, np.nan, np.nan
        calculators['calc_macd'] = calc_macd
        
        # RSI指标
        calculators['calc_rsi'] = lambda data, period: talib.RSI(data, timeperiod=period) if len(data) >= period else np.nan
        
        # 布林带指标
        def calc_bbands(data):
            if len(data) >= 20:
                upper, middle, lower = talib.BBANDS(data, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
                return upper, middle, lower
            return np.nan, np.nan, np.nan
        calculators['calc_bbands'] = calc_bbands
        
        # KDJ指标
        def calc_kdj(high, low, close):
            if len(high) >= 9 and len(low) >= 9 and len(close) >= 9:  # STOCH K period
                k, d = talib.STOCH(high, low, close, fastk_period=9, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
                return k, d, 3 * k - 2 * d
            return np.nan, np.nan, np.nan
        calculators['calc_kdj'] = calc_kdj
        
        # 威廉指标
        def calc_wr(high, low, close, period):
            if len(high) >= period and len(low) >= period and len(close) >= period:
                return talib.WILLR(high, low, close, timeperiod=period)
            return np.nan
        calculators['calc_wr'] = calc_wr
        
        # CCI指标
        def calc_cci(high, low, close, period):
            if len(high) >= period and len(low) >= period and len(close) >= period:
                return talib.CCI(high, low, close, timeperiod=period)
            return np.nan
        calculators['calc_cci'] = calc_cci
        
        # DMI指标
        def calc_dmi(high, low, close, period):
            if len(high) >= period and len(low) >= period and len(close) >= period:
                pdi = talib.PLUS_DI(high, low, close, timeperiod=period)
                mdi = talib.MINUS_DI(high, low, close, timeperiod=period)
                adx = talib.ADX(high, low, close, timeperiod=period)
                return pdi, mdi, adx
            return np.nan, np.nan, np.nan
        calculators['calc_dmi'] = calc_dmi
        
        # ROC指标
        calculators['calc_roc'] = lambda data, period: talib.ROC(data, timeperiod=period) if len(data) >= period else np.nan
        
        # BIAS指标
        def calc_bias(data, period):
            if len(data) >= period:
                ma = talib.SMA(data, timeperiod=period)
                # BIAS = (收盘价 - MA) / MA * 100
                bias = (data - ma) / ma * 100
                return bias
            return np.nan
        calculators['calc_bias'] = calc_bias
        
        # OBV指标
        def calc_obv(close, volume):
            if len(close) >= 2 and len(volume) >= 2:
                obv = talib.OBV(close, volume)
                obv_ma5 = talib.SMA(obv, timeperiod=5) if len(obv) >= 5 else np.nan
                obv_ma10 = talib.SMA(obv, timeperiod=10) if len(obv) >= 10 else np.nan
                return obv, obv_ma5, obv_ma10
            return np.nan, np.nan, np.nan
        calculators['calc_obv'] = calc_obv
        
        # ATR指标
        def calc_atr(high, low, close, period):
            if len(high) >= period and len(low) >= period and len(close) >= period:
                return talib.ATR(high, low, close, timeperiod=period)
            return np.nan
        calculators['calc_atr'] = calc_atr
        
        # 最高价和最低价
        calculators['calc_highest'] = lambda data, period: pd.Series(data).rolling(window=period).max().values if len(data) >= period else np.nan
        calculators['calc_lowest'] = lambda data, period: pd.Series(data).rolling(window=period).min().values if len(data) >= period else np.nan
        
        return calculators

    @staticmethod
    @performance_monitor
    def _calculate_indicators_for_group(group_df, entity_id_col_name):
        """为单个股票/行业/指数的数据计算指标"""
        # 最短周期指标SMA5至少需要5个数据点。如果数据点少于5，则无法计算任何有意义的指标。
        # 后续的 dropna(subset=['SMA5'], how='all') 会移除SMA5为NaN的行。
        if len(group_df) < 5:
            logger.debug(f"实体 {group_df[entity_id_col_name].iloc[0] if not group_df.empty else 'N/A'} "
                         f"数据点不足 ({len(group_df)} < 5)，跳过指标计算。")
            return pd.DataFrame()

        open_prices = group_df['open'].values.astype(float)
        high_prices = group_df['high'].values.astype(float)
        low_prices = group_df['low'].values.astype(float)
        close_prices = group_df['close'].values.astype(float)
        volume = group_df['volume'].values.astype(float)

        indicators = pd.DataFrame(index=group_df.index)
        indicators[entity_id_col_name] = group_df[entity_id_col_name]
        indicators['日期'] = group_df['日期']

        # 获取所有指标计算函数
        calculators = TechnicalIndicatorCalculator._get_indicator_calculators()
        
        # 从计算函数中提取需要的函数
        calc_sma = calculators['calc_sma']
        calc_ema = calculators['calc_ema']
        calc_macd = calculators['calc_macd']
        calc_rsi = calculators['calc_rsi']
        calc_bbands = calculators['calc_bbands']
        calc_kdj = calculators['calc_kdj']
        calc_wr = calculators['calc_wr']
        calc_cci = calculators['calc_cci']
        calc_dmi = calculators['calc_dmi']
        calc_roc = calculators['calc_roc']
        calc_bias = calculators['calc_bias']
        calc_obv = calculators['calc_obv']
        calc_atr = calculators['calc_atr']
        calc_highest = calculators['calc_highest']
        calc_lowest = calculators['calc_lowest']

        # 计算基本指标
        indicators['SMA5'] = calc_sma(close_prices, 5)
        indicators['SMA10'] = calc_sma(close_prices, 10)
        indicators['SMA20'] = calc_sma(close_prices, 20)
        indicators['SMA60'] = calc_sma(close_prices, 60)
        indicators['EMA12'] = calc_ema(close_prices, 12)
        indicators['EMA26'] = calc_ema(close_prices, 26)
        indicators['DIF'], indicators['DEA'], indicators['MACD_hist'] = calc_macd(close_prices)
        indicators['RSI6'] = calc_rsi(close_prices, 6)
        indicators['RSI12'] = calc_rsi(close_prices, 12)
        indicators['RSI24'] = calc_rsi(close_prices, 24)
        indicators['BBANDS_UPPER'], indicators['BBANDS_MIDDLE'], indicators['BBANDS_LOWER'] = calc_bbands(close_prices)
        indicators['KDJ_K'], indicators['KDJ_D'], indicators['KDJ_J'] = calc_kdj(high_prices, low_prices, close_prices)
        indicators['VOL_MA5'] = calc_sma(volume, 5)
        indicators['VOL_MA10'] = calc_sma(volume, 10)
        
        indicators.replace([np.inf, -np.inf], np.nan, inplace=True) # Replace inf with NaN
        
        # 计算新增指标
        indicators['WR14'] = calc_wr(high_prices, low_prices, close_prices, 14)
        indicators['CCI14'] = calc_cci(high_prices, low_prices, close_prices, 14)
        indicators['PDI14'], indicators['MDI14'], indicators['ADX14'] = calc_dmi(high_prices, low_prices, close_prices, 14)
        indicators['ROC6'] = calc_roc(close_prices, 6)
        indicators['ROC12'] = calc_roc(close_prices, 12)
        indicators['BIAS6'] = calc_bias(close_prices, 6)
        indicators['BIAS12'] = calc_bias(close_prices, 12)
        indicators['BIAS24'] = calc_bias(close_prices, 24)
        indicators['OBV'], indicators['OBV_MA5'], indicators['OBV_MA10'] = calc_obv(close_prices, volume)
        
        # 计算海龟交易策略所需的指标
        indicators['ATR14'] = calc_atr(high_prices, low_prices, close_prices, 14)
        indicators['ATR20'] = calc_atr(high_prices, low_prices, close_prices, 20)
        indicators['HIGHEST_20'] = calc_highest(high_prices, 20)
        indicators['HIGHEST_55'] = calc_highest(high_prices, 55)
        indicators['LOWEST_10'] = calc_lowest(low_prices, 10)
        indicators['LOWEST_20'] = calc_lowest(low_prices, 20)
        
        # 定义实际计算的指标列列表
        indicator_cols = ['SMA5', 'SMA10', 'SMA20', 'SMA60', 'EMA12', 'EMA26',
                          'DIF', 'DEA', 'MACD_hist', 'RSI6', 'RSI12', 'RSI24',
                          'BBANDS_UPPER', 'BBANDS_MIDDLE', 'BBANDS_LOWER',
                          'KDJ_K', 'KDJ_D', 'KDJ_J', 'VOL_MA5', 'VOL_MA10',
                          'WR14', 'CCI14', 'PDI14', 'MDI14', 'ADX14',
                          'ROC6', 'ROC12', 'BIAS6', 'BIAS12', 'BIAS24',
                          'OBV', 'OBV_MA5', 'OBV_MA10',
                          'ATR14', 'ATR20', 'HIGHEST_20', 'HIGHEST_55', 'LOWEST_10', 'LOWEST_20']
        # 仅当所有这些指标都为NaN时才删除行
        return indicators.dropna(subset=indicator_cols, how='all')

    def _store_indicators(self, df_indicators, data_type):
        """将计算出的指标存储到数据库
        
        该方法支持动态处理新增的技术指标，会自动从DataFrame中获取所有指标列，
        并使用TableStructureManager确保表结构中存在这些列。
        """
        if df_indicators.empty:
            logger.info(f"没有指标数据可为 {data_type} 存储。")
            return

        table_name_unquoted = ""
        # Primary key column names, unquoted (matching DataFrame column names)
        pk_cols_df = [] 

        if data_type == 'stock':
            table_name_unquoted = '股票技术指标'
            pk_cols_df = ['股票代码', '日期'] 
        elif data_type == 'industry':
            table_name_unquoted = '行业技术指标'
            pk_cols_df = ['行业名称', '日期']
        elif data_type == 'index':
            table_name_unquoted = '指数技术指标'
            pk_cols_df = ['指数代码', '日期']
        else:
            logger.error(f"无效的data_type {data_type} 用于存储指标。")
            return
            
        # 使用TableStructureManager确保表结构中存在所有指标列
        if hasattr(self, 'table_manager') and self.table_manager:
            try:
                # 获取所有指标列（排除主键列）
                indicator_columns = [col for col in df_indicators.columns if col not in pk_cols_df]
                
                # 使用TableStructureManager添加缺失的指标列
                logger.info(f"检查并添加{data_type}技术指标表中缺失的指标列")
                
                # 获取当前表的列
                current_columns = [col[0] for col in self.table_manager.get_table_columns(table_name_unquoted)]
                
                # 逐个添加缺失的列
                added_columns = []
                failed_columns = []
                
                for col in indicator_columns:
                    if col not in current_columns:
                        success = self.table_manager.add_column(table_name_unquoted, col, 'DOUBLE PRECISION')
                        if success:
                            added_columns.append(col)
                        else:
                            failed_columns.append(col)
                
                if added_columns:
                    logger.info(f"成功添加 {len(added_columns)} 个新指标列到 {table_name_unquoted} 表: {', '.join(added_columns)}")
                if failed_columns:
                    logger.warning(f"添加指标列失败: {', '.join(failed_columns)}")
            except Exception as e:
                logger.error(f"检查并添加指标列时出错: {e}")

        # Operate on a copy for modifications
        df_to_insert = df_indicators.copy()

        # Ensure '日期' is in the correct string format for SQL if it's datetime
        if '日期' in df_to_insert.columns and pd.api.types.is_datetime64_any_dtype(df_to_insert['日期']):
            df_to_insert['日期'] = df_to_insert['日期'].dt.strftime('%Y-%m-%d')

        # Replace NaN with None for SQL compatibility
        df_to_insert.replace({np.nan: None}, inplace=True)
        
        # Convert DataFrame to list of tuples for executemany (used in simplified psycopg2 path)
        data_tuples = [tuple(x) for x in df_to_insert.to_numpy()]

        if self.dry_run:
            logger.info(f"[DRY RUN] Would insert/update {len(data_tuples)} rows into public.\"{table_name_unquoted}\"")
            return

        try:
            if self.pg_manager:
                # For PostgreSQLManager, column names in DataFrame and lists should be unquoted.
                # The manager should handle quoting internally if necessary.
                update_columns_unquoted_for_manager = [col for col in df_to_insert.columns if col not in pk_cols_df]
                
                success = self.pg_manager.insert_df(
                    table_name_unquoted,      # Unquoted table name
                    df_to_insert,             # DataFrame with unquoted column names
                    conflict_columns=pk_cols_df, # Unquoted PK columns
                    update_columns=update_columns_unquoted_for_manager # Unquoted update columns
                )
                if success:
                    #logger.info(f"成功存储指标数据到 public.\"{table_name_unquoted}\" (via pg_manager)")
                    pass
                else:
                    logger.error(f"存储指标数据到 public.\"{table_name_unquoted}\" 失败 (via pg_manager)")
            else:
                # For simplified psycopg2 path, SQL needs quoted identifiers.
                sql_table_name_quoted = f'public."{table_name_unquoted}"'
                sql_cols_quoted = [f'"{c}"' for c in df_to_insert.columns] # All df columns quoted for SQL
                sql_pk_cols_quoted = [f'"{c}"' for c in pk_cols_df] # PK columns from df, quoted for SQL
                
                conflict_target_sql = f"({', '.join(sql_pk_cols_quoted)})"
                
                # Update columns for SQL are those not in primary key, and need quoting
                update_cols_for_sql_df_names = [col for col in df_to_insert.columns if col not in pk_cols_df]
                update_cols_sql_quoted = [f'"{c}"' for c in update_cols_for_sql_df_names]
                update_set_sql = ', '.join([f'{col_quoted} = EXCLUDED.{col_quoted}' for col_quoted in update_cols_sql_quoted])
                
                placeholders = ', '.join(['%s'] * len(sql_cols_quoted))
                insert_query_simplified = f'INSERT INTO {sql_table_name_quoted} ({', '.join(sql_cols_quoted)}) VALUES %s ON CONFLICT {conflict_target_sql} DO UPDATE SET {update_set_sql}'

                self._connect_db()
                psycopg2.extras.execute_values(self.cursor, insert_query_simplified, data_tuples)
                self.conn.commit()
                #logger.info(f"成功存储指标数据到 {sql_table_name_quoted} (simplified path)")
        except Exception as e:
            logger.error(f"存储指标数据到 {sql_table_name_quoted} 失败: {e}")
            if self.conn and not self.pg_manager: # Rollback only for simplified connection
                self.conn.rollback()

    @performance_monitor
    def process_data_type(self, data_type, entity_ids=None):
        """处理指定数据类型的所有实体或特定实体的技术指标计算"""
        logger.info(f"开始处理 {data_type} 技术指标计算...")
        id_column_df = ""
        if data_type == 'stock':
            id_column_df = '股票代码'
        elif data_type == 'industry':
            id_column_df = '行业名称'
        elif data_type == 'index':
            id_column_df = '指数代码'
        else:
            logger.error(f"不支持的数据类型: {data_type}")
            return

        # 如果未提供entity_ids，则获取所有实体ID
        if not entity_ids:
            source_table = ''
            if data_type == 'stock':
                source_table = 'public."股票基本信息"'
            elif data_type == 'industry':
                source_table = 'public."行业板块"' # 假设有这样一个表
            elif data_type == 'index':
                source_table = 'public."指数历史行情"' # 实际应从指数历史行情表获取代码
            
            if source_table:
                query = f"SELECT DISTINCT \"{id_column_df}\" FROM {source_table}"
                try:
                    all_entities_df = pd.DataFrame()
                    if self.pg_manager:
                        all_entities_df = self.pg_manager.query_df(query)
                    else:
                        self._connect_db()
                        all_entities_df = pd.read_sql_query(query, self.conn)
                    
                    if not all_entities_df.empty:
                        entity_ids = all_entities_df[id_column_df].tolist()
                    else:
                        logger.warning(f"未能从 {source_table} 获取实体列表，将尝试从历史行情数据中获取。")
                except Exception as e:
                    logger.error(f"从 {source_table} 获取实体列表失败: {e}，将尝试从历史行情数据中获取。")
            
            # 如果从基本信息表获取失败或没有这些表，尝试从历史数据表获取
            if not entity_ids:
                hist_table_map = {
                    'stock': 'public."股票历史行情_后复权"',
                    'industry': 'public."行业历史行情"',
                    'index': 'public."指数历史行情"'
                }
                hist_table = hist_table_map.get(data_type)
                if hist_table:
                    query_hist = f"SELECT DISTINCT \"{id_column_df}\" FROM {hist_table}"
                    try:
                        all_entities_hist_df = pd.DataFrame()
                        if self.pg_manager:
                            all_entities_hist_df = self.pg_manager.query_df(query_hist)
                        else:
                            self._connect_db()
                            all_entities_hist_df = pd.read_sql_query(query_hist, self.conn)
                        if not all_entities_hist_df.empty:
                            entity_ids = all_entities_hist_df[id_column_df].tolist()
                        else:
                            logger.warning(f"未能从 {hist_table} 获取实体列表。")
                            return # 没有实体ID，无法继续
                    except Exception as e:
                        logger.error(f"从 {hist_table} 获取实体列表失败: {e}")
                        return # 没有实体ID，无法继续
                else:
                    logger.error(f"无法确定用于获取实体ID的历史行情表: {data_type}")
                    return

        if not entity_ids:
            logger.warning(f"没有找到 {data_type} 类型的实体ID进行处理。")
            return

        logger.info(f"将为 {len(entity_ids)} 个 {data_type} 实体计算指标。")

        # 分批处理实体以避免内存问题和过长的数据库查询
        batch_size = 50 # 可根据实际情况调整
        for i in tqdm(range(0, len(entity_ids), batch_size), desc=f"处理 {data_type} 批次"):
            batch_entity_ids = entity_ids[i:i+batch_size]
            historical_data_df = self._fetch_historical_data(data_type, batch_entity_ids)

            if historical_data_df.empty:
                logger.warning(f"未能获取 {data_type} 批次数据，跳过处理。")
                continue

            results_list = []
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {}
                for entity_id, group_df in historical_data_df.groupby(id_column_df):
                    # 提交静态方法，而非实例方法
                    future = executor.submit(
                        TechnicalIndicatorCalculator._calculate_indicators_for_group,
                        group_df.copy(),
                        id_column_df
                    )
                    futures[future] = entity_id

                # 处理计算结果
                for future in tqdm(as_completed(futures), total=len(futures), desc=f"计算 {data_type} 批次 (共{len(batch_entity_ids)}个实体) 指标", leave=False):
                    entity_id_for_log = futures[future]
                    try:
                        indicators_df_result = future.result()
                        if indicators_df_result is not None and not indicators_df_result.empty:
                            results_list.append(indicators_df_result)
                    except Exception as e:
                        logger.error(f"为实体 {entity_id_for_log} 计算指标时出错: {e}", exc_info=True)
            
            if results_list:
                all_indicators_df = pd.concat(results_list, ignore_index=True)
                if not all_indicators_df.empty:
                    self._store_indicators(all_indicators_df, data_type)
                else:
                    logger.info(f"当前批次 ({data_type}, 实体: {batch_entity_ids}) 合并后没有计算出任何有效指标数据。")
            else:
                logger.info(f"当前批次 ({data_type}, 实体: {batch_entity_ids}) 没有计算出任何指标数据。")

        logger.info(f"{data_type} 技术指标计算完成。")

    def run(self, data_types=None, entity_ids_map=None, specific_entities=None):
        """运行技术指标计算的主函数

        Args:
            data_types (list, optional): 要处理的数据类型列表 ('stock', 'industry', 'index'). 
                                         如果为 None, 则处理所有类型。
            entity_ids_map (dict, optional): 一个字典，键是数据类型，值是该类型的实体ID列表。
                                           例如: {'stock': ['000001', '000002']}
            specific_entities (dict, optional): 命令行传入的特定实体，格式同 entity_ids_map
        """
        # 创建技术指标表并检查表结构
        self._create_indicator_tables()
        
        if data_types is None:
            data_types = ['stock', 'industry', 'index']

        # 检查是否有新增的技术指标需要添加到表结构中
        if hasattr(self, 'table_manager') and self.table_manager and not self.dry_run:
            try:
                # 定义需要添加的指标列
                indicator_tables = []
                if 'stock' in data_types:
                    indicator_tables.append('股票技术指标')
                if 'industry' in data_types:
                    indicator_tables.append('行业技术指标')
                if 'index' in data_types:
                    indicator_tables.append('指数技术指标')
                
                # 检查并修复表结构
                for table_name in indicator_tables:
                    logger.info(f"检查表 {table_name} 结构并添加缺失的指标列")
                    check_result = self.table_manager.check_table_structure(table_name)
                    if check_result['exists'] and not check_result['structure_ok']:
                        fix_result = self.table_manager.fix_table_structure(table_name)
                        if fix_result['success']:
                            logger.info(f"表 {table_name} 结构修复成功，添加了 {len(fix_result['added_columns'])} 个列")
                        else:
                            logger.error(f"表 {table_name} 结构修复失败: {fix_result['error']}")
            except Exception as e:
                logger.error(f"检查和修复表结构失败: {e}")

        final_entity_ids_map = {}
        if entity_ids_map:
            final_entity_ids_map.update(entity_ids_map)
        if specific_entities:
            for dt, ids in specific_entities.items():
                if dt in final_entity_ids_map:
                    # 如果命令行和代码都指定了，合并并去重
                    final_entity_ids_map[dt] = list(set(final_entity_ids_map[dt] + ids))
                else:
                    final_entity_ids_map[dt] = ids

        for data_type in data_types:
            ids_to_process = final_entity_ids_map.get(data_type)
            self.process_data_type(data_type, entity_ids=ids_to_process)

        self._close_db()

def main():
    parser = argparse.ArgumentParser(description="计算并存储股票、行业、指数的技术指标")
    parser.add_argument("--data-type", type=str, nargs='+', 
                        choices=['stock', 'industry', 'index'], 
                        help="要计算的数据类型 (例如: stock industry)")
    parser.add_argument("--stock-ids", type=str, nargs='+', help="要计算的特定股票代码 (例如: 000001 600000)")
    parser.add_argument("--industry-names", type=str, nargs='+', help="要计算的特定行业名称 (例如: '银行' '证券')")
    parser.add_argument("--index-codes", type=str, nargs='+', help="要计算的特定指数代码 (例如: sh000001 sz399001)")
    parser.add_argument("--dry-run", action='store_true', help="执行空跑，不写入数据库")

    args = parser.parse_args()

    try:
        db_params = load_db_config()
    except Exception as e:
        logger.error(f"加载数据库配置失败: {e}")
        sys.exit(1)

    calculator = TechnicalIndicatorCalculator(db_config=db_params, dry_run=args.dry_run)

    data_types_to_process = args.data_type
    specific_entities = {}
    if args.stock_ids:
        specific_entities['stock'] = args.stock_ids
    if args.industry_names:
        specific_entities['industry'] = args.industry_names
    if args.index_codes:
        specific_entities['index'] = args.index_codes

    # 如果没有通过命令行指定数据类型，但指定了特定实体，则从实体类型推断
    if not data_types_to_process and specific_entities:
        data_types_to_process = list(specific_entities.keys())
    elif not data_types_to_process:
        data_types_to_process = ['stock', 'industry', 'index'] # 默认处理所有
    
    logger.info(f"将要处理的数据类型: {data_types_to_process}")
    if specific_entities:
        logger.info("将处理指定的特定实体")

    try:
        calculator.run(data_types=data_types_to_process, specific_entities=specific_entities)
    except Exception as e:
        logger.error(f"技术指标计算过程中发生严重错误: {e}", exc_info=True)
    finally:
        logger.info("技术指标计算脚本执行完毕。")

if __name__ == "__main__":
    main()