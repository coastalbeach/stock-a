#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
定义策略基类和接口，提供对多元数据的访问支持
"""

from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union
import os
import sys

# 添加项目根目录到系统路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from db import EnhancedPostgreSQLManager

class StrategyBase(ABC):
    """策略基类，提供对多元数据的访问支持"""

    def __init__(self, name: str):
        """
        初始化策略

        Args:
            name (str): 策略名称
        """
        self._name = name
        self._db_manager = None

    @property
    def name(self) -> str:
        """获取策略名称"""
        return self._name
    
    @property
    def db_manager(self) -> EnhancedPostgreSQLManager:
        """获取数据库管理器，如果未初始化则创建一个新的实例"""
        if self._db_manager is None:
            self._db_manager = EnhancedPostgreSQLManager()
        return self._db_manager

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号

        Args:
            data (pd.DataFrame): 输入的行情数据，至少应包含 '日期', '股票代码', '开盘', '收盘', '最高', '最低', '成交量' 等列。
                                 具体需要的列取决于策略本身。

        Returns:
            pd.DataFrame: 包含交易信号的DataFrame。该DataFrame应至少包含以下列：
                          - '日期' (datetime): 信号产生的日期。
                          - '股票代码' (str): 信号对应的股票代码。
                          - '信号类型' (str): 交易信号的类型，例如 '买入', '卖出', '持仓'。
                          - '信号价格' (float, optional): 触发信号时的价格，例如买入价或卖出价。
                          - '信号强度' (float, optional): 信号的强度或置信度 (0到1之间)。
                          - '备注' (str, optional): 与信号相关的其他备注信息。
        """
        pass
    
    # ========== 数据访问方法 ==========
    
    def get_stock_quotes(self, stock_code: str, start_date: Optional[str] = None, 
                        end_date: Optional[str] = None, limit: int = 60) -> pd.DataFrame:
        """获取股票行情数据
        
        Args:
            stock_code (str): 股票代码
            start_date (str, optional): 开始日期，格式为'YYYY-MM-DD'
            end_date (str, optional): 结束日期，格式为'YYYY-MM-DD'
            limit (int, optional): 返回记录数量限制，默认为60
            
        Returns:
            pd.DataFrame: 股票行情数据
        """
        return self.db_manager.read_stock_quotes(stock_code, start_date, end_date, limit)
    
    def get_technical_indicators(self, stock_code: str, indicators: Optional[List[str]] = None, 
                               start_date: Optional[str] = None, end_date: Optional[str] = None, 
                               limit: int = 60) -> pd.DataFrame:
        """获取技术指标数据
        
        Args:
            stock_code (str): 股票代码
            indicators (list, optional): 要查询的指标列表，如['SMA5', 'SMA10', 'RSI6']
            start_date (str, optional): 开始日期，格式为'YYYY-MM-DD'
            end_date (str, optional): 结束日期，格式为'YYYY-MM-DD'
            limit (int, optional): 返回记录数量限制，默认为60
            
        Returns:
            pd.DataFrame: 技术指标数据
        """
        return self.db_manager.read_technical_indicators(stock_code, indicators, start_date, end_date, limit)
    
    def get_financial_statement(self, statement_type: str, stock_code: Optional[str] = None, 
                              report_date: Optional[str] = None, limit: int = 4) -> pd.DataFrame:
        """获取财务报表数据
        
        Args:
            statement_type (str): 报表类型，如'资产负债表'、'利润表'、'现金流量表'
            stock_code (str, optional): 股票代码
            report_date (str, optional): 报告期，格式为'YYYY-MM-DD'
            limit (int, optional): 返回记录数量限制，默认为4
            
        Returns:
            pd.DataFrame: 财务报表数据
        """
        return self.db_manager.read_financial_statement(statement_type, stock_code, report_date, limit)
    
    def get_financial_ratios(self, stock_code: str, report_date: Optional[str] = None) -> Dict[str, Any]:
        """获取财务指标
        
        Args:
            stock_code (str): 股票代码
            report_date (str, optional): 报告期，格式为'YYYY-MM-DD'，不指定则获取最新报告期
            
        Returns:
            dict: 财务指标数据
        """
        return self.db_manager.get_financial_ratios(stock_code, report_date)
    
    def get_stock_info(self, stock_code: Optional[str] = None, stock_name: Optional[str] = None, 
                      industry: Optional[str] = None) -> pd.DataFrame:
        """获取股票基本信息
        
        Args:
            stock_code (str, optional): 股票代码
            stock_name (str, optional): 股票名称
            industry (str, optional): 所属行业
            
        Returns:
            pd.DataFrame: 股票基本信息
        """
        return self.db_manager.read_stock_info(stock_code, stock_name, industry)
    
    def get_industry_info(self, industry_code: Optional[str] = None, 
                        industry_name: Optional[str] = None) -> pd.DataFrame:
        """获取行业信息
        
        Args:
            industry_code (str, optional): 行业代码
            industry_name (str, optional): 行业名称
            
        Returns:
            pd.DataFrame: 行业信息
        """
        return self.db_manager.read_industry_info(industry_code, industry_name)
    
    def get_concept_info(self, concept_code: Optional[str] = None, 
                       concept_name: Optional[str] = None) -> pd.DataFrame:
        """获取概念信息
        
        Args:
            concept_code (str, optional): 概念代码
            concept_name (str, optional): 概念名称
            
        Returns:
            pd.DataFrame: 概念信息
        """
        return self.db_manager.read_concept_info(concept_code, concept_name)
    
    def get_index_quotes(self, index_code: str, start_date: Optional[str] = None, 
                        end_date: Optional[str] = None, limit: int = 60) -> pd.DataFrame:
        """获取指数行情数据
        
        Args:
            index_code (str): 指数代码
            start_date (str, optional): 开始日期，格式为'YYYY-MM-DD'
            end_date (str, optional): 结束日期，格式为'YYYY-MM-DD'
            limit (int, optional): 返回记录数量限制，默认为60
            
        Returns:
            pd.DataFrame: 指数行情数据
        """
        return self.db_manager.read_index_quotes(index_code, start_date, end_date, limit)
    
    def get_dragon_tiger_list(self, stock_code: Optional[str] = None, 
                            trade_date: Optional[str] = None, 
                            limit: int = 50) -> pd.DataFrame:
        """获取龙虎榜数据
        
        Args:
            stock_code (str, optional): 股票代码
            trade_date (str, optional): 交易日期，格式为'YYYY-MM-DD'
            limit (int, optional): 返回记录数量限制，默认为50
            
        Returns:
            pd.DataFrame: 龙虎榜数据
        """
        return self.db_manager.read_dragon_tiger_list(stock_code, trade_date, limit)
    
    def get_table_data(self, table_name: str, conditions: Optional[Dict[str, Any]] = None, 
                      order_by: Optional[List[str]] = None, order_desc: bool = False, 
                      limit: Optional[int] = None, offset: Optional[int] = None) -> pd.DataFrame:
        """获取任意表数据
        
        Args:
            table_name (str): 表名
            conditions (dict, optional): 查询条件，键为列名，值为查询值
            order_by (list, optional): 排序列名列表
            order_desc (bool, optional): 是否降序排序
            limit (int, optional): 返回记录数量限制
            offset (int, optional): 返回记录起始偏移量
            
        Returns:
            pd.DataFrame: 表数据
        """
        return self.db_manager.read_table(table_name, conditions, order_by, order_desc, limit, offset)
    
    def close_db_connection(self):
        """关闭数据库连接"""
        if self._db_manager is not None:
            self._db_manager.close()
            self._db_manager = None

    def __repr__(self):
        return f"Strategy(name='{self.name}')"

    def __str__(self):
        return self.name