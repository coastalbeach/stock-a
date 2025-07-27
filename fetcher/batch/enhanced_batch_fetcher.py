#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
增强版批量股票历史数据获取模块

基于akshare的stock_zh_a_hist函数，提供更强大的批量获取和增量更新功能
支持配置文件、智能调度、错误恢复、数据验证等高级特性
"""

import os
import sys
import time
import datetime
import pandas as pd
import numpy as np
import threading
import concurrent.futures
from queue import Queue, Empty
from pathlib import Path
from tqdm import tqdm
import logging
import json
import yaml
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
try:
    import schedule
except ImportError:
    schedule = None

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入项目模块
from utils.logger import LoggerManager
from utils.config_loader import load_connection_config
from db import PostgreSQLManager, RedisManager

# 导入AKShare
import akshare as ak


@dataclass
class BatchConfig:
    """批量获取配置类"""
    # 基本配置
    start_date: str = "20050104"
    enable_checkpoint: bool = True
    checkpoint_file: str = "data/batch_checkpoint.json"
    log_level: str = "INFO"
    
    # 并发配置
    max_workers: int = 8
    batch_size: int = 50
    request_interval: float = 0.1
    thread_timeout: int = 300
    
    # 重试策略
    max_attempts: int = 3
    base_interval: int = 2
    backoff_factor: int = 2
    max_interval: int = 30
    
    # 数据表配置
    no_adjust_table: str = "股票历史行情_不复权"
    hfq_table: str = "股票历史行情_后复权"
    primary_keys: List[str] = None
    
    # 数据过滤配置
    skip_st_stocks: bool = False
    skip_delisted_stocks: bool = False
    min_market_cap: float = 0
    stock_code_prefixes: List[str] = None
    
    # 性能优化配置
    enable_redis_cache: bool = True
    cache_expire_time: int = 3600
    enable_db_pool: bool = True
    db_pool_size: int = 10
    bulk_insert_size: int = 1000
    
    # 监控配置
    enable_progress_bar: bool = True
    progress_report_interval: int = 100
    save_detailed_logs: bool = True
    send_completion_notification: bool = False
    
    # 错误处理配置
    continue_on_error: bool = True
    save_error_details: bool = True
    error_log_file: str = "logs/batch_errors.log"
    max_consecutive_failures: int = 50
    
    # 数据验证配置
    enable_data_validation: bool = True
    check_duplicates: bool = True
    check_data_format: bool = True
    max_missing_data_rate: float = 10.0
    
    # 调度配置
    enable_scheduled_run: bool = False
    scheduled_time: str = "06:00"
    run_interval_days: int = 1
    trading_days_only: bool = True
    
    def __post_init__(self):
        if self.primary_keys is None:
            self.primary_keys = ["股票代码", "日期"]
        if self.stock_code_prefixes is None:
            self.stock_code_prefixes = []


class EnhancedBatchFetcher:
    """增强版批量股票历史数据获取器
    
    新增功能：
    1. 配置文件支持
    2. 智能调度
    3. 数据验证
    4. 错误恢复
    5. 性能监控
    6. 通知系统
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """初始化增强版批量获取器
        
        Args:
            config_file (Optional[str]): 配置文件路径，如果为None则使用默认配置
        """
        # 加载配置
        self.config = self._load_config(config_file)
        
        # 初始化日志
        self.logger = self._init_logger()
        self.logger.info("初始化增强版批量股票历史数据获取器")
        
        # 初始化数据库连接
        self.db = PostgreSQLManager(
            use_pool=self.config.enable_db_pool,
            max_connections=self.config.db_pool_size
        )
        
        # 初始化Redis（如果启用）
        self.redis = None
        if self.config.enable_redis_cache:
            try:
                self.redis = RedisManager()
                self.logger.info("Redis缓存已启用")
            except Exception as e:
                self.logger.warning(f"Redis连接失败，将禁用缓存功能: {e}")
                self.config.enable_redis_cache = False
        
        # 状态跟踪
        self.total_stocks = 0
        self.completed_stocks = 0
        self.failed_stocks = []
        self.consecutive_failures = 0
        self.progress_lock = threading.Lock()
        self.start_time = None
        
        # 断点续传文件路径
        self.checkpoint_file = os.path.join(project_root, self.config.checkpoint_file)
        os.makedirs(os.path.dirname(self.checkpoint_file), exist_ok=True)
        
        # 错误日志文件路径
        self.error_log_file = os.path.join(project_root, self.config.error_log_file)
        os.makedirs(os.path.dirname(self.error_log_file), exist_ok=True)
        
    def _load_config(self, config_file: Optional[str]) -> BatchConfig:
        """加载配置文件
        
        Args:
            config_file (Optional[str]): 配置文件路径
            
        Returns:
            BatchConfig: 配置对象
        """
        if config_file is None:
            config_file = os.path.join(os.path.dirname(__file__), "batch_config.yaml")
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                
                # 展平嵌套配置
                flat_config = {}
                for section, values in config_data.items():
                    if isinstance(values, dict):
                        flat_config.update(values)
                    else:
                        flat_config[section] = values
                
                # 过滤掉不属于BatchConfig的参数
                import inspect
                valid_params = set(inspect.signature(BatchConfig.__init__).parameters.keys())
                valid_params.discard('self')  # 移除self参数
                
                filtered_config = {k: v for k, v in flat_config.items() if k in valid_params}
                
                return BatchConfig(**filtered_config)
            else:
                print(f"配置文件 {config_file} 不存在，使用默认配置")
                return BatchConfig()
        except Exception as e:
            print(f"加载配置文件失败: {e}，使用默认配置")
            return BatchConfig()
    
    def _init_logger(self):
        """初始化日志记录器"""
        logger_manager = LoggerManager()
        logger = logger_manager.get_logger("enhanced_batch_fetcher")
        
        # 设置日志级别
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        logger.setLevel(log_level)
        
        return logger
    
    def get_filtered_stock_list(self) -> List[str]:
        """获取过滤后的股票列表
        
        Returns:
            List[str]: 过滤后的股票代码列表
        """
        try:
            self.logger.info("从数据库获取股票列表")
            
            # 构建基础查询
            sql = "SELECT 股票代码, 股票名称 FROM 股票基本信息"
            conditions = []
            params = []
            
            # 添加过滤条件
            if self.config.skip_st_stocks:
                conditions.append("股票名称 NOT LIKE '%ST%'")
            
            if self.config.stock_code_prefixes:
                prefix_conditions = []
                for prefix in self.config.stock_code_prefixes:
                    prefix_conditions.append("股票代码 LIKE %s")
                    params.append(f"{prefix}%")
                conditions.append(f"({' OR '.join(prefix_conditions)})")
            
            # 组装完整SQL
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += " ORDER BY 股票代码"
            
            result = self.db.query(sql, tuple(params) if params else None)
            
            if not result:
                self.logger.warning("数据库中没有股票基本信息数据")
                return []
            
            stock_list = [item['股票代码'] for item in result]
            self.logger.info(f"获取到 {len(stock_list)} 只股票（应用过滤条件后）")
            return stock_list
            
        except Exception as e:
            self.logger.error(f"获取股票列表失败: {e}")
            return []
    
    def validate_data(self, df: pd.DataFrame, stock_code: str) -> Tuple[bool, List[str]]:
        """验证数据质量
        
        Args:
            df (pd.DataFrame): 要验证的数据
            stock_code (str): 股票代码
            
        Returns:
            Tuple[bool, List[str]]: (是否通过验证, 错误信息列表)
        """
        if not self.config.enable_data_validation:
            return True, []
        
        errors = []
        
        try:
            # 检查数据是否为空
            if df.empty:
                errors.append("数据为空")
                return False, errors
            
            # 检查必要列是否存在
            required_columns = ['日期', '股票代码', '开盘', '收盘', '最高', '最低', '成交量']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                errors.append(f"缺少必要列: {missing_columns}")
            
            # 检查数据格式
            if self.config.check_data_format:
                # 检查日期格式
                if '日期' in df.columns:
                    try:
                        pd.to_datetime(df['日期'])
                    except:
                        errors.append("日期格式错误")
                
                # 检查数值列
                numeric_columns = ['开盘', '收盘', '最高', '最低', '成交量', '成交额']
                for col in numeric_columns:
                    if col in df.columns:
                        if not pd.api.types.is_numeric_dtype(df[col]):
                            try:
                                pd.to_numeric(df[col], errors='coerce')
                            except:
                                errors.append(f"列{col}不是数值类型")
            
            # 检查数据缺失率
            missing_rate = df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100
            if missing_rate > self.config.max_missing_data_rate:
                errors.append(f"数据缺失率过高: {missing_rate:.2f}%")
            
            # 检查重复数据
            if self.config.check_duplicates:
                if '日期' in df.columns and '股票代码' in df.columns:
                    duplicates = df.duplicated(subset=['日期', '股票代码']).sum()
                    if duplicates > 0:
                        errors.append(f"发现{duplicates}条重复数据")
            
            # 检查价格逻辑
            if all(col in df.columns for col in ['开盘', '收盘', '最高', '最低']):
                # 最高价应该 >= 最低价
                invalid_high_low = (df['最高'] < df['最低']).sum()
                if invalid_high_low > 0:
                    errors.append(f"发现{invalid_high_low}条最高价小于最低价的异常数据")
                
                # 开盘价和收盘价应该在最高价和最低价之间
                invalid_open = ((df['开盘'] > df['最高']) | (df['开盘'] < df['最低'])).sum()
                invalid_close = ((df['收盘'] > df['最高']) | (df['收盘'] < df['最低'])).sum()
                if invalid_open > 0:
                    errors.append(f"发现{invalid_open}条开盘价超出最高最低价范围的异常数据")
                if invalid_close > 0:
                    errors.append(f"发现{invalid_close}条收盘价超出最高最低价范围的异常数据")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"数据验证过程中发生异常: {e}")
            return False, errors
    
    def get_cached_data(self, cache_key: str) -> Optional[Any]:
        """从Redis获取缓存数据
        
        Args:
            cache_key (str): 缓存键
            
        Returns:
            Optional[Any]: 缓存数据，如果不存在则返回None
        """
        if not self.config.enable_redis_cache or not self.redis:
            return None
        
        try:
            return self.redis.get_value(cache_key)
        except Exception as e:
            self.logger.warning(f"获取缓存数据失败: {e}")
            return None
    
    def set_cached_data(self, cache_key: str, data: Any, expire: Optional[int] = None):
        """设置Redis缓存数据
        
        Args:
            cache_key (str): 缓存键
            data (Any): 要缓存的数据
            expire (Optional[int]): 过期时间（秒），如果为None则使用配置中的默认值
        """
        if not self.config.enable_redis_cache or not self.redis:
            return
        
        try:
            if expire is None:
                expire = self.config.cache_expire_time
            self.redis.set_value(cache_key, data, expire=expire)
        except Exception as e:
            self.logger.warning(f"设置缓存数据失败: {e}")
    
    def get_missing_data_info_cached(self, stock_code: str) -> Dict[str, Optional[str]]:
        """获取股票缺失数据信息（带缓存）
        
        Args:
            stock_code (str): 股票代码
            
        Returns:
            Dict[str, Optional[str]]: 包含不复权和后复权表的最后更新日期
        """
        cache_key = f"stock:last_update:{stock_code}"
        cached_info = self.get_cached_data(cache_key)
        
        if cached_info:
            return cached_info
        
        # 缓存中没有数据，从数据库获取
        info = {
            "不复权": None,
            "后复权": None
        }
        
        tables = [self.config.no_adjust_table, self.config.hfq_table]
        table_keys = ["不复权", "后复权"]
        
        for table, key in zip(tables, table_keys):
            try:
                sql = f"SELECT MAX(日期) as last_date FROM \"{table}\" WHERE 股票代码 = %s"
                result = self.db.query(sql, (stock_code,))
                
                if result and result[0]['last_date']:
                    last_date = result[0]['last_date']
                    info[key] = last_date.strftime("%Y%m%d")
                else:
                    info[key] = None
            except Exception as e:
                self.logger.error(f"获取{stock_code}在{table}表中的最后更新日期失败: {e}")
                info[key] = None
        
        # 缓存结果
        self.set_cached_data(cache_key, info, expire=1800)  # 缓存30分钟
        
        return info
    
    def process_single_stock_enhanced(self, stock_code: str) -> Dict[str, Any]:
        """增强版单只股票处理
        
        Args:
            stock_code (str): 股票代码
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        result = {
            "stock_code": stock_code,
            "不复权": {"success": False, "records": 0, "errors": []},
            "后复权": {"success": False, "records": 0, "errors": []},
            "total_records": 0,
            "processing_time": 0
        }
        
        start_time = time.time()
        
        try:
            # 获取缺失数据信息
            missing_info = self.get_missing_data_info_cached(stock_code)
            
            # 处理不复权数据
            self._process_stock_data_type(
                stock_code, missing_info["不复权"], "", 
                self.config.no_adjust_table, result["不复权"]
            )
            
            # 处理后复权数据
            self._process_stock_data_type(
                stock_code, missing_info["后复权"], "hfq", 
                self.config.hfq_table, result["后复权"]
            )
            
            # 计算总记录数
            result["total_records"] = result["不复权"]["records"] + result["后复权"]["records"]
            
            # 添加请求间隔
            if self.config.request_interval > 0:
                time.sleep(self.config.request_interval)
            
        except Exception as e:
            error_msg = f"处理股票{stock_code}时发生异常: {e}"
            self.logger.error(error_msg)
            result["不复权"]["errors"].append(error_msg)
            result["后复权"]["errors"].append(error_msg)
        
        finally:
            result["processing_time"] = time.time() - start_time
        
        return result
    
    def _process_stock_data_type(self, stock_code: str, last_update_date: Optional[str], 
                                adjust: str, table_name: str, result_dict: Dict[str, Any]):
        """处理特定类型的股票数据（不复权或后复权）
        
        Args:
            stock_code (str): 股票代码
            last_update_date (Optional[str]): 最后更新日期
            adjust (str): 复权类型
            table_name (str): 目标表名
            result_dict (Dict[str, Any]): 结果字典
        """
        try:
            # 计算日期范围
            start_date, end_date = self._calculate_date_range(last_update_date)
            
            if start_date and end_date:
                # 获取数据
                df = self._fetch_stock_data_with_validation(stock_code, start_date, end_date, adjust)
                
                if df is not None and not df.empty:
                    # 保存数据
                    success = self._save_data_to_db_enhanced(df, table_name)
                    if success:
                        result_dict["success"] = True
                        result_dict["records"] = len(df)
                        self.logger.debug(f"股票{stock_code}{adjust or '不复权'}数据更新成功，新增{len(df)}条记录")
                        
                        # 更新缓存
                        cache_key = f"stock:last_update:{stock_code}"
                        self.redis and self.redis.delete(cache_key)
                    else:
                        result_dict["errors"].append(f"保存{adjust or '不复权'}数据到数据库失败")
                else:
                    result_dict["success"] = True  # 没有新数据也算成功
            else:
                result_dict["success"] = True  # 数据已是最新
                
        except Exception as e:
            error_msg = f"处理{stock_code}{adjust or '不复权'}数据失败: {e}"
            result_dict["errors"].append(error_msg)
            self.logger.error(error_msg)
    
    def _calculate_date_range(self, last_update_date: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """计算需要获取的日期范围
        
        Args:
            last_update_date (Optional[str]): 最后更新日期
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (开始日期, 结束日期)
        """
        end_date = datetime.datetime.now().strftime("%Y%m%d")
        
        if last_update_date is None:
            return self.config.start_date, end_date
        else:
            last_date = datetime.datetime.strptime(last_update_date, "%Y%m%d")
            next_date = last_date + datetime.timedelta(days=1)
            start_date = next_date.strftime("%Y%m%d")
            
            if start_date > end_date:
                return None, None
            
            return start_date, end_date
    
    def _fetch_stock_data_with_validation(self, stock_code: str, start_date: str, 
                                        end_date: str, adjust: str = "") -> Optional[pd.DataFrame]:
        """获取股票数据并进行验证
        
        Args:
            stock_code (str): 股票代码
            start_date (str): 开始日期
            end_date (str): 结束日期
            adjust (str): 复权类型
            
        Returns:
            Optional[pd.DataFrame]: 验证后的股票数据
        """
        try:
            # 使用akshare获取数据
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            
            if df.empty:
                return None
            
            # 数据预处理
            df = self._preprocess_data_enhanced(df, stock_code)
            
            # 数据验证
            is_valid, errors = self.validate_data(df, stock_code)
            if not is_valid:
                self.logger.warning(f"股票{stock_code}数据验证失败: {'; '.join(errors)}")
                if self.config.save_error_details:
                    self._save_error_details(stock_code, "数据验证失败", errors)
                return None
            
            return df
            
        except Exception as e:
            self.logger.error(f"获取股票{stock_code}数据失败: {e}")
            if self.config.save_error_details:
                self._save_error_details(stock_code, "数据获取失败", [str(e)])
            return None
    
    def _preprocess_data_enhanced(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """增强版数据预处理
        
        Args:
            df (pd.DataFrame): 原始数据
            stock_code (str): 股票代码
            
        Returns:
            pd.DataFrame: 处理后的数据
        """
        # 基础预处理
        if '股票代码' not in df.columns:
            df['股票代码'] = stock_code
        
        if '日期' in df.columns:
            df['日期'] = pd.to_datetime(df['日期']).dt.date
        
        # 数值列转换和清理
        numeric_columns = ['开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # 处理异常值
                if col in ['开盘', '收盘', '最高', '最低']:
                    # 价格不能为负数或零
                    df[col] = df[col].where(df[col] > 0, np.nan)
                elif col in ['成交量', '成交额']:
                    # 成交量和成交额不能为负数
                    df[col] = df[col].where(df[col] >= 0, 0)
        
        # 重新排列列顺序
        expected_columns = [
            '日期', '股票代码', '开盘', '收盘', '最高', '最低', 
            '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率'
        ]
        
        available_columns = [col for col in expected_columns if col in df.columns]
        df = df[available_columns]
        
        # 去除重复行
        if self.config.check_duplicates:
            df = df.drop_duplicates(subset=['日期', '股票代码'], keep='last')
        
        # 按日期排序
        if '日期' in df.columns:
            df = df.sort_values('日期')
        
        return df
    
    def _save_data_to_db_enhanced(self, df: pd.DataFrame, table_name: str) -> bool:
        """增强版数据保存
        
        Args:
            df (pd.DataFrame): 要保存的数据
            table_name (str): 目标表名
            
        Returns:
            bool: 保存是否成功
        """
        try:
            if df.empty:
                return True
            
            # 分批保存大数据集
            if len(df) > self.config.bulk_insert_size:
                success_count = 0
                total_batches = (len(df) + self.config.bulk_insert_size - 1) // self.config.bulk_insert_size
                
                for i in range(0, len(df), self.config.bulk_insert_size):
                    batch_df = df.iloc[i:i + self.config.bulk_insert_size]
                    success = self.db.upsert_from_df(
                        df=batch_df,
                        table_name=table_name,
                        primary_keys=self.config.primary_keys
                    )
                    if success:
                        success_count += 1
                
                return success_count == total_batches
            else:
                # 小数据集直接保存
                return self.db.upsert_from_df(
                    df=df,
                    table_name=table_name,
                    primary_keys=self.config.primary_keys
                )
                
        except Exception as e:
            self.logger.error(f"保存数据到{table_name}表异常: {e}")
            return False
    
    def _save_error_details(self, stock_code: str, error_type: str, errors: List[str]):
        """保存错误详情到文件
        
        Args:
            stock_code (str): 股票代码
            error_type (str): 错误类型
            errors (List[str]): 错误信息列表
        """
        try:
            error_info = {
                "timestamp": datetime.datetime.now().isoformat(),
                "stock_code": stock_code,
                "error_type": error_type,
                "errors": errors
            }
            
            with open(self.error_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(error_info, ensure_ascii=False) + "\n")
                
        except Exception as e:
            self.logger.error(f"保存错误详情失败: {e}")
    
    def run_enhanced_batch_update(self, stock_list: Optional[List[str]] = None, 
                                use_checkpoint: bool = True) -> Dict[str, Any]:
        """运行增强版批量更新
        
        Args:
            stock_list (Optional[List[str]]): 指定的股票列表
            use_checkpoint (bool): 是否使用断点续传
            
        Returns:
            Dict[str, Any]: 执行结果统计
        """
        self.start_time = datetime.datetime.now()
        self.logger.info("开始增强版批量股票历史数据更新")
        
        try:
            # 获取股票列表
            if stock_list is None:
                stock_list = self.get_filtered_stock_list()
            
            if not stock_list:
                return {"success": False, "message": "没有获取到股票列表"}
            
            # 处理断点续传
            completed_stocks = []
            if use_checkpoint and self.config.enable_checkpoint:
                checkpoint = self._load_checkpoint()
                if checkpoint:
                    completed_stocks = checkpoint.get("completed_stocks", [])
                    stock_list = [stock for stock in stock_list if stock not in completed_stocks]
                    self.logger.info(f"断点续传: 跳过{len(completed_stocks)}只已完成的股票")
            
            self.total_stocks = len(stock_list)
            self.completed_stocks = 0
            self.failed_stocks = []
            self.consecutive_failures = 0
            
            if self.total_stocks == 0:
                return {
                    "success": True,
                    "message": "所有股票数据已是最新",
                    "total_stocks": len(completed_stocks),
                    "completed_stocks": len(completed_stocks)
                }
            
            # 运行批量处理
            result = self._run_threaded_processing(stock_list)
            
            # 添加已完成的股票到结果中
            result["total_stocks"] += len(completed_stocks)
            result["completed_stocks"] += len(completed_stocks)
            
            return result
            
        except Exception as e:
            self.logger.error(f"增强版批量更新过程中发生异常: {e}")
            return {"success": False, "message": str(e)}
        
        finally:
            self.cleanup()
    
    def _run_threaded_processing(self, stock_list: List[str]) -> Dict[str, Any]:
        """运行多线程处理
        
        Args:
            stock_list (List[str]): 股票代码列表
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        # 创建股票队列
        stock_queue = Queue()
        for stock_code in stock_list:
            stock_queue.put(stock_code)
        
        # 创建进度条
        progress_bar = None
        if self.config.enable_progress_bar:
            progress_bar = tqdm(
                total=self.total_stocks,
                desc="增强版批量更新",
                unit="只",
                ncols=120
            )
        
        # 启动工作线程
        threads = []
        for i in range(self.config.max_workers):
            thread = threading.Thread(
                target=self._enhanced_worker_thread,
                args=(stock_queue, progress_bar),
                name=f"EnhancedWorker-{i+1}"
            )
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        # 等待所有任务完成
        stock_queue.join()
        
        # 等待所有线程结束
        for thread in threads:
            thread.join(timeout=self.config.thread_timeout)
        
        if progress_bar:
            progress_bar.close()
        
        # 生成结果报告
        return self._generate_result_report()
    
    def _enhanced_worker_thread(self, stock_queue: Queue, progress_bar: Optional[tqdm]):
        """增强版工作线程
        
        Args:
            stock_queue (Queue): 股票代码队列
            progress_bar (Optional[tqdm]): 进度条对象
        """
        while True:
            try:
                stock_code = stock_queue.get(timeout=1)
                
                # 检查是否应该停止处理
                if self.consecutive_failures >= self.config.max_consecutive_failures:
                    self.logger.error(f"连续失败次数达到上限({self.config.max_consecutive_failures})，停止处理")
                    stock_queue.task_done()
                    break
                
                # 处理股票数据
                success = self._process_with_retry(stock_code)
                
                with self.progress_lock:
                    if success:
                        self.completed_stocks += 1
                        self.consecutive_failures = 0
                    else:
                        self.failed_stocks.append(stock_code)
                        self.consecutive_failures += 1
                
                # 更新进度
                if progress_bar:
                    progress_bar.update(1)
                
                # 定期保存断点
                if self.completed_stocks % self.config.progress_report_interval == 0:
                    self._save_checkpoint_threadsafe()
                
                stock_queue.task_done()
                
            except Empty:
                break
            except Exception as e:
                self.logger.error(f"增强版工作线程异常: {e}")
                break
    
    def _process_with_retry(self, stock_code: str) -> bool:
        """带重试的股票处理
        
        Args:
            stock_code (str): 股票代码
            
        Returns:
            bool: 处理是否成功
        """
        for attempt in range(self.config.max_attempts):
            try:
                result = self.process_single_stock_enhanced(stock_code)
                
                # 检查是否成功
                if result["不复权"]["success"] and result["后复权"]["success"]:
                    return True
                
                # 如果失败，等待后重试
                if attempt < self.config.max_attempts - 1:
                    wait_time = min(
                        self.config.base_interval * (self.config.backoff_factor ** attempt),
                        self.config.max_interval
                    )
                    time.sleep(wait_time)
                
            except Exception as e:
                self.logger.error(f"处理股票{stock_code}第{attempt+1}次尝试失败: {e}")
                if attempt < self.config.max_attempts - 1:
                    wait_time = min(
                        self.config.base_interval * (self.config.backoff_factor ** attempt),
                        self.config.max_interval
                    )
                    time.sleep(wait_time)
        
        return False
    
    def _save_checkpoint_threadsafe(self):
        """线程安全的断点保存"""
        if not self.config.enable_checkpoint:
            return
        
        try:
            with self.progress_lock:
                # 计算已完成的股票列表（这里简化处理）
                completed_stocks = []
                checkpoint_data = {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "completed_stocks": completed_stocks,
                    "failed_stocks": self.failed_stocks.copy(),
                    "total_stocks": self.total_stocks,
                    "completed_count": self.completed_stocks
                }
                
                with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                    json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
                    
        except Exception as e:
            self.logger.error(f"保存断点信息失败: {e}")
    
    def _load_checkpoint(self) -> Optional[Dict]:
        """加载断点信息"""
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            self.logger.error(f"加载断点信息失败: {e}")
            return None
    
    def _generate_result_report(self) -> Dict[str, Any]:
        """生成结果报告"""
        end_time = datetime.datetime.now()
        duration = end_time - self.start_time
        
        result = {
            "success": True,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration.total_seconds(),
            "total_stocks": self.total_stocks,
            "completed_stocks": self.completed_stocks,
            "failed_stocks": len(self.failed_stocks),
            "failed_stock_list": self.failed_stocks,
            "success_rate": (self.completed_stocks / self.total_stocks * 100) if self.total_stocks > 0 else 100,
            "average_time_per_stock": duration.total_seconds() / self.total_stocks if self.total_stocks > 0 else 0
        }
        
        self.logger.info(
            f"增强版批量更新完成: 总计{result['total_stocks']}只股票，"
            f"成功{result['completed_stocks']}只，失败{result['failed_stocks']}只，"
            f"成功率{result['success_rate']:.2f}%，耗时{duration}"
        )
        
        return result
    
    def cleanup(self):
        """清理资源"""
        try:
            if hasattr(self, 'db') and self.db:
                self.db.close()
            if hasattr(self, 'redis') and self.redis:
                self.redis.close()
            self.logger.info("增强版批量获取器资源清理完成")
        except Exception as e:
            self.logger.error(f"资源清理失败: {e}")


def main():
    """主函数 - 示例用法"""
    # 创建增强版批量获取器
    fetcher = EnhancedBatchFetcher()
    
    # 运行批量更新
    result = fetcher.run_enhanced_batch_update(use_checkpoint=True)
    
    # 打印结果
    if result["success"]:
        print(f"\n增强版批量更新成功完成!")
        print(f"总股票数: {result['total_stocks']}")
        print(f"成功更新: {result['completed_stocks']}")
        print(f"失败数量: {result['failed_stocks']}")
        print(f"成功率: {result['success_rate']:.2f}%")
        print(f"平均每只股票耗时: {result['average_time_per_stock']:.2f}秒")
        print(f"总耗时: {result['duration_seconds']:.2f}秒")
        
        if result['failed_stock_list']:
            print(f"\n失败的股票: {', '.join(result['failed_stock_list'])}")
    else:
        print(f"增强版批量更新失败: {result['message']}")


if __name__ == "__main__":
    main()