# -*- coding: utf-8 -*-
"""
回测数据处理器

负责处理回测所需的各种数据源，包括股票行情、技术指标、财务数据等
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
import logging

# 添加项目根目录到系统路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from db import EnhancedPostgreSQLManager, RedisManager
from utils.logger import LoggerManager


class DataProcessor:
    """
    回测数据处理器
    
    负责获取、处理和缓存回测所需的各种数据
    """
    
    def __init__(self, use_cache: bool = True):
        """
        初始化数据处理器
        
        Args:
            use_cache (bool): 是否使用缓存
        """
        self.db_manager = EnhancedPostgreSQLManager()
        self.redis_manager = RedisManager() if use_cache else None
        self.use_cache = use_cache
        
        # 获取日志记录器
        logger_manager = LoggerManager()
        self.logger = logger_manager.get_logger('data_processor')
        
        # 数据缓存
        self.data_cache = {}
        
        self.logger.info("数据处理器初始化完成")
    
    def get_stock_data(self, stock_code: str, start_date: str, end_date: str, 
                      data_source: str = 'database', adjust: str = 'qfq') -> pd.DataFrame:
        """
        获取股票行情数据
        
        Args:
            stock_code (str): 股票代码
            start_date (str): 开始日期，格式为'YYYY-MM-DD'
            end_date (str): 结束日期，格式为'YYYY-MM-DD'
            data_source (str): 数据源，'database' 或 'akshare'
            adjust (str): 复权类型，'qfq'(前复权)、'hfq'(后复权)、'none'(不复权)
            
        Returns:
            pd.DataFrame: 股票行情数据
        """
        cache_key = f"stock_data:{stock_code}:{start_date}:{end_date}:{data_source}:{adjust}"
        
        # 检查缓存
        if self.use_cache and cache_key in self.data_cache:
            self.logger.debug(f"从内存缓存获取数据: {stock_code}")
            return self.data_cache[cache_key].copy()
        
        # 检查Redis缓存
        if self.use_cache and self.redis_manager:
            cached_data = self.redis_manager.get_dataframe(cache_key)
            if cached_data is not None:
                self.logger.debug(f"从Redis缓存获取数据: {stock_code}")
                self.data_cache[cache_key] = cached_data
                return cached_data.copy()
        
        try:
            if data_source == 'database':
                data = self._get_stock_data_from_database(stock_code, start_date, end_date)
            else:
                data = self._get_stock_data_from_akshare(stock_code, start_date, end_date, adjust)
            
            if not data.empty:
                # 数据预处理
                data = self._preprocess_stock_data(data)
                
                # 缓存数据
                if self.use_cache:
                    self.data_cache[cache_key] = data
                    if self.redis_manager:
                        # 缓存1小时
                        self.redis_manager.set_dataframe(cache_key, data, expire=3600)
                
                self.logger.info(f"获取股票数据成功: {stock_code}, 数据量: {len(data)}")
            else:
                self.logger.warning(f"未获取到股票数据: {stock_code}")
            
            return data
            
        except Exception as e:
            self.logger.error(f"获取股票数据失败: {stock_code}, 错误: {e}")
            return pd.DataFrame()
    
    def _get_stock_data_from_database(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        从数据库获取股票数据
        
        Args:
            stock_code (str): 股票代码
            start_date (str): 开始日期
            end_date (str): 结束日期
            
        Returns:
            pd.DataFrame: 股票数据
        """
        return self.db_manager.read_stock_quotes(stock_code, start_date, end_date, limit=None)
    
    def _get_stock_data_from_akshare(self, stock_code: str, start_date: str, end_date: str, adjust: str = 'qfq') -> pd.DataFrame:
        """
        从AKShare获取股票数据
        
        Args:
            stock_code (str): 股票代码
            start_date (str): 开始日期
            end_date (str): 结束日期
            adjust (str): 复权类型
            
        Returns:
            pd.DataFrame: 股票数据
        """
        try:
            import akshare as ak
            
            # 获取股票历史数据
            data = ak.stock_zh_a_hist(
                symbol=stock_code, 
                period="daily", 
                start_date=start_date.replace('-', ''), 
                end_date=end_date.replace('-', ''), 
                adjust=adjust
            )
            
            if not data.empty:
                # 重命名列以匹配数据库格式
                column_mapping = {
                    '日期': '日期',
                    '开盘': '开盘',
                    '收盘': '收盘',
                    '最高': '最高',
                    '最低': '最低',
                    '成交量': '成交量',
                    '成交额': '成交额',
                    '振幅': '振幅',
                    '涨跌幅': '涨跌幅',
                    '涨跌额': '涨跌额',
                    '换手率': '换手率'
                }
                
                # 只保留存在的列
                available_columns = {k: v for k, v in column_mapping.items() if k in data.columns}
                data = data[list(available_columns.keys())].rename(columns=available_columns)
                
                # 添加股票代码
                data['股票代码'] = stock_code
            
            return data
            
        except Exception as e:
            self.logger.error(f"从AKShare获取数据失败: {e}")
            return pd.DataFrame()
    
    def _preprocess_stock_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        预处理股票数据
        
        Args:
            data (pd.DataFrame): 原始股票数据
            
        Returns:
            pd.DataFrame: 预处理后的数据
        """
        if data.empty:
            return data
        
        # 确保日期列存在且格式正确
        if '日期' in data.columns:
            data['日期'] = pd.to_datetime(data['日期'])
        
        # 确保数值列为数值类型
        numeric_columns = ['开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']
        for col in numeric_columns:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')
        
        # 删除包含NaN的行
        data = data.dropna(subset=['开盘', '收盘', '最高', '最低'])
        
        # 按日期排序
        if '日期' in data.columns:
            data = data.sort_values('日期')
        
        # 重置索引
        data = data.reset_index(drop=True)
        
        return data
    
    def get_technical_indicators(self, stock_code: str, indicators: Optional[List[str]] = None,
                               start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取技术指标数据
        
        Args:
            stock_code (str): 股票代码
            indicators (List[str], optional): 指标列表
            start_date (str, optional): 开始日期
            end_date (str, optional): 结束日期
            
        Returns:
            pd.DataFrame: 技术指标数据
        """
        cache_key = f"indicators:{stock_code}:{indicators}:{start_date}:{end_date}"
        
        # 检查缓存
        if self.use_cache and cache_key in self.data_cache:
            return self.data_cache[cache_key].copy()
        
        try:
            data = self.db_manager.read_technical_indicators(
                stock_code, indicators, start_date, end_date, limit=None
            )
            
            if not data.empty:
                # 缓存数据
                if self.use_cache:
                    self.data_cache[cache_key] = data
                
                self.logger.debug(f"获取技术指标成功: {stock_code}, 指标数量: {len(data.columns)}")
            
            return data
            
        except Exception as e:
            self.logger.error(f"获取技术指标失败: {stock_code}, 错误: {e}")
            return pd.DataFrame()
    
    def get_financial_data(self, stock_code: str, statement_type: str = 'balance_sheet',
                          report_date: Optional[str] = None, periods: int = 4) -> pd.DataFrame:
        """
        获取财务数据
        
        Args:
            stock_code (str): 股票代码
            statement_type (str): 财务报表类型
            report_date (str, optional): 报告期
            periods (int): 获取期数
            
        Returns:
            pd.DataFrame: 财务数据
        """
        cache_key = f"financial:{stock_code}:{statement_type}:{report_date}:{periods}"
        
        # 检查缓存
        if self.use_cache and cache_key in self.data_cache:
            return self.data_cache[cache_key].copy()
        
        try:
            data = self.db_manager.read_financial_statement(
                statement_type, stock_code, report_date, limit=periods
            )
            
            if not data.empty:
                # 缓存数据
                if self.use_cache:
                    self.data_cache[cache_key] = data
                
                self.logger.debug(f"获取财务数据成功: {stock_code}, 数据量: {len(data)}")
            
            return data
            
        except Exception as e:
            self.logger.error(f"获取财务数据失败: {stock_code}, 错误: {e}")
            return pd.DataFrame()
    
    def get_market_data(self, market_type: str = 'index', start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取市场数据（指数、板块等）
        
        Args:
            market_type (str): 市场数据类型
            start_date (str, optional): 开始日期
            end_date (str, optional): 结束日期
            
        Returns:
            pd.DataFrame: 市场数据
        """
        cache_key = f"market:{market_type}:{start_date}:{end_date}"
        
        # 检查缓存
        if self.use_cache and cache_key in self.data_cache:
            return self.data_cache[cache_key].copy()
        
        try:
            # 这里可以根据需要实现不同类型的市场数据获取
            # 暂时返回空DataFrame
            data = pd.DataFrame()
            
            if not data.empty:
                # 缓存数据
                if self.use_cache:
                    self.data_cache[cache_key] = data
            
            return data
            
        except Exception as e:
            self.logger.error(f"获取市场数据失败: {market_type}, 错误: {e}")
            return pd.DataFrame()
    
    def combine_data(self, stock_data: pd.DataFrame, indicator_data: Optional[pd.DataFrame] = None,
                    financial_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        合并不同类型的数据
        
        Args:
            stock_data (pd.DataFrame): 股票行情数据
            indicator_data (pd.DataFrame, optional): 技术指标数据
            financial_data (pd.DataFrame, optional): 财务数据
            
        Returns:
            pd.DataFrame: 合并后的数据
        """
        try:
            result = stock_data.copy()
            
            # 合并技术指标数据
            if indicator_data is not None and not indicator_data.empty:
                # 确保都有日期和股票代码列
                merge_columns = ['日期', '股票代码'] if '股票代码' in indicator_data.columns else ['日期']
                result = pd.merge(result, indicator_data, on=merge_columns, how='left')
            
            # 合并财务数据（按季度合并）
            if financial_data is not None and not financial_data.empty:
                # 财务数据通常按季度发布，需要特殊处理
                result = self._merge_financial_data(result, financial_data)
            
            self.logger.debug(f"数据合并完成，最终数据量: {len(result)}")
            return result
            
        except Exception as e:
            self.logger.error(f"数据合并失败: {e}")
            return stock_data
    
    def _merge_financial_data(self, stock_data: pd.DataFrame, financial_data: pd.DataFrame) -> pd.DataFrame:
        """
        合并财务数据
        
        Args:
            stock_data (pd.DataFrame): 股票数据
            financial_data (pd.DataFrame): 财务数据
            
        Returns:
            pd.DataFrame: 合并后的数据
        """
        try:
            # 确保财务数据有报告期列
            if '报告期' not in financial_data.columns:
                return stock_data
            
            # 将报告期转换为日期
            financial_data['报告期'] = pd.to_datetime(financial_data['报告期'])
            
            # 为股票数据添加对应的财务数据
            result = stock_data.copy()
            
            # 为每个交易日找到最近的财务报告期
            for idx, row in result.iterrows():
                trade_date = pd.to_datetime(row['日期'])
                stock_code = row.get('股票代码', '')
                
                # 找到该股票在该日期之前最近的财务数据
                stock_financial = financial_data[
                    (financial_data['股票代码'] == stock_code) & 
                    (financial_data['报告期'] <= trade_date)
                ]
                
                if not stock_financial.empty:
                    # 取最近的一期财务数据
                    latest_financial = stock_financial.loc[stock_financial['报告期'].idxmax()]
                    
                    # 添加财务指标到结果中
                    for col in financial_data.columns:
                        if col not in ['股票代码', '报告期']:
                            result.loc[idx, col] = latest_financial[col]
            
            return result
            
        except Exception as e:
            self.logger.error(f"合并财务数据失败: {e}")
            return stock_data
    
    def validate_data(self, data: pd.DataFrame, required_columns: List[str]) -> bool:
        """
        验证数据完整性
        
        Args:
            data (pd.DataFrame): 待验证的数据
            required_columns (List[str]): 必需的列
            
        Returns:
            bool: 数据是否有效
        """
        if data.empty:
            self.logger.warning("数据为空")
            return False
        
        # 检查必需列
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            self.logger.warning(f"缺少必需列: {missing_columns}")
            return False
        
        # 检查数据质量
        for col in required_columns:
            if col in ['开盘', '收盘', '最高', '最低']:
                # 检查价格数据的合理性
                if (data[col] <= 0).any():
                    self.logger.warning(f"发现非正价格数据: {col}")
                    return False
        
        self.logger.debug("数据验证通过")
        return True
    
    def clear_cache(self):
        """
        清空缓存
        """
        self.data_cache.clear()
        if self.redis_manager:
            # 这里可以实现Redis缓存清理逻辑
            pass
        self.logger.info("缓存已清空")