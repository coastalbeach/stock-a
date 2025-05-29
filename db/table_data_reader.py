#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
表数据读取器

提供对所有数据表的统一读取接口，支持灵活的查询条件、分页和排序
该模块基于PostgreSQLManager和EnhancedPostgreSQLManager，提供更高级的数据读取功能
"""

import os
import sys
import yaml
import logging
import pandas as pd
import datetime
from pathlib import Path
from typing import List, Dict, Any, Union, Optional, Tuple

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent)  # db/table_data_reader.py -> stock-a
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入数据库管理器
from db.enhanced_postgresql_manager import EnhancedPostgreSQLManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TableDataReader')


class TableDataReader:
    """表数据读取器类
    
    提供对所有数据表的统一读取接口，支持灵活的查询条件、分页和排序
    """
    
    def __init__(self, debug_mode=False):
        """初始化表数据读取器
        
        Args:
            debug_mode (bool, optional): 是否启用调试模式，默认为False
        """
        self.db = EnhancedPostgreSQLManager()
        self.tables_config = self._load_tables_config()
        self.debug_mode = debug_mode
        
        if self.debug_mode:
            logger.setLevel(logging.DEBUG)
            logger.debug("表数据读取器已启用调试模式")
        
        logger.info("表数据读取器初始化完成")
        print("=== 表数据读取器已初始化 ===")
        print("提供对所有数据表的统一读取接口，支持灵活的查询条件、分页和排序")
    
    def _load_tables_config(self) -> Dict[str, Any]:
        """加载表配置
        
        Returns:
            Dict[str, Any]: 表配置字典
        """
        config_path = os.path.join(project_root, 'config', 'tables.yaml')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.debug(f"成功加载表配置，共 {len(config.get('tables', {}))} 个表")
            return config
        except Exception as e:
            logger.error(f"加载表配置失败: {e}")
            return {'tables': {}}
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """获取表信息
        
        Args:
            table_name (str): 表名
            
        Returns:
            Dict[str, Any]: 表信息字典，包含列定义、主键、索引等
        """
        tables = self.tables_config.get('tables', {})
        if table_name in tables:
            return tables[table_name]
        else:
            logger.warning(f"表 {table_name} 在配置中不存在")
            return {}
    
    def get_all_tables(self) -> List[str]:
        """获取所有表名
        
        Returns:
            List[str]: 所有表名列表
        """
        return list(self.tables_config.get('tables', {}).keys())
    
    def read_table(self, table_name: str, conditions: Dict[str, Any] = None, 
                  columns: List[str] = None, limit: int = 1000, 
                  offset: int = 0, order_by: List[str] = None,
                  order_desc: bool = False) -> pd.DataFrame:
        """读取表数据
        
        Args:
            table_name (str): 表名
            conditions (Dict[str, Any], optional): 查询条件，格式为 {列名: 值} 或 {列名: (操作符, 值)}
            columns (List[str], optional): 要查询的列名列表，默认为所有列
            limit (int, optional): 返回记录数量限制，默认为1000
            offset (int, optional): 返回记录的偏移量，默认为0
            order_by (List[str], optional): 排序列名列表
            order_desc (bool, optional): 是否降序排序，默认为False
            
        Returns:
            pandas.DataFrame: 查询结果DataFrame
        """
        try:
            # 检查表是否存在
            if not self.db.table_exists(table_name):
                logger.error(f"表 {table_name} 不存在")
                return pd.DataFrame()
            
            # 构建查询列
            if columns:
                columns_str = '", "'.join(columns)
                select_clause = f'"{columns_str}"'
            else:
                select_clause = '*'
            
            # 构建查询条件
            where_clause = ""
            params = []
            
            if conditions:
                conditions_list = []
                
                for col, value in conditions.items():
                    if isinstance(value, tuple) and len(value) == 2:
                        operator, val = value
                        conditions_list.append(f'"{col}" {operator} %s')
                        params.append(val)
                    else:
                        conditions_list.append(f'"{col}" = %s')
                        params.append(value)
                
                if conditions_list:
                    where_clause = "WHERE " + " AND ".join(conditions_list)
            
            # 构建排序子句
            order_clause = ""
            if order_by:
                direction = "DESC" if order_desc else "ASC"
                order_items = [f'"{col}" {direction}' for col in order_by]
                order_clause = "ORDER BY " + ", ".join(order_items)
            
            # 构建完整SQL
            sql = f'SELECT {select_clause} FROM "{table_name}" {where_clause} {order_clause} LIMIT {limit} OFFSET {offset}'
            
            if self.debug_mode:
                logger.debug(f"执行SQL: {sql}")
                logger.debug(f"参数: {params}")
            
            # 执行查询
            return self.db.query_df(sql, tuple(params) if params else None)
        except Exception as e:
            logger.error(f"读取表 {table_name} 数据失败: {e}")
            if self.debug_mode:
                import traceback
                logger.debug(traceback.format_exc())
            return pd.DataFrame()
    
    def read_financial_statement(self, table_name: str, stock_code: str, 
                               report_date: str = None, report_type: str = None) -> pd.DataFrame:
        """读取财务报表数据
        
        适用于资产负债表、利润表、现金流量表等财务报表
        
        Args:
            table_name (str): 表名，如"资产负债表"、"利润表"、"现金流量表"
            stock_code (str): 股票代码
            report_date (str, optional): 报告期，格式为'YYYY-MM-DD'，不指定则获取最新报告期
            report_type (str, optional): 报表类型，如"年报"、"季报"，不指定则获取所有类型
            
        Returns:
            pandas.DataFrame: 查询结果DataFrame
        """
        conditions = {"股票代码": stock_code}
        
        if report_date:
            conditions["报告期"] = report_date
        
        if report_type:
            conditions["报表类型"] = report_type
        
        # 如果没有指定报告期，则按报告期降序排序并限制返回最新的记录
        order_by = ["报告期"]
        order_desc = True if not report_date else False
        limit = 1 if not report_date and not report_type else 10
        
        return self.read_table(table_name, conditions, order_by=order_by, 
                              order_desc=order_desc, limit=limit)
    
    def _check_table_exists(self, table_name: str) -> bool:
        """检查表是否存在
        
        Args:
            table_name (str): 表名
            
        Returns:
            bool: 表是否存在
        """
        try:
            query = f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """
            result = self.db.query(query, (table_name,))
            return result[0][0] if result else False
        except Exception as e:
            logging.error(f"检查表 {table_name} 是否存在时出错: {e}")
            return False
        
    def read_historical_data(self, table_name: str, conditions: Dict[str, Any] = None,
                           start_date: str = None, end_date: str = None,
                           date_col_name: str = "日期", limit: int = 60,
                           order_desc: bool = True) -> pd.DataFrame:
        """通用历史数据读取方法
        
        可用于读取任何包含日期列的历史数据表，如股票、行业、指数的历史行情数据
        
        Args:
            table_name (str): 表名
            conditions (Dict[str, Any], optional): 查询条件，格式为 {列名: 值} 或 {列名: (操作符, 值)}
            start_date (str, optional): 开始日期，格式为'YYYY-MM-DD'
            end_date (str, optional): 结束日期，格式为'YYYY-MM-DD'
            date_col_name (str, optional): 日期列名，默认为"日期"
            limit (int, optional): 返回记录数量限制，默认为60
            order_desc (bool, optional): 是否降序排序，默认为True
            
        Returns:
            pandas.DataFrame: 查询结果DataFrame
        """
        """通用历史数据读取方法
        
        可用于读取任何包含日期列的历史数据表，如股票、行业、指数的历史行情数据
        
        Args:
            table_name (str): 表名
            conditions (Dict[str, Any], optional): 查询条件，格式为 {列名: 值} 或 {列名: (操作符, 值)}
            start_date (str, optional): 开始日期，格式为'YYYY-MM-DD'
            end_date (str, optional): 结束日期，格式为'YYYY-MM-DD'
            date_col_name (str, optional): 日期列名，默认为"日期"
            limit (int, optional): 返回记录数量限制，默认为60
            order_desc (bool, optional): 是否降序排序，默认为True
            
        Returns:
            pandas.DataFrame: 查询结果DataFrame
        """
        # 记录调试信息
        logging.debug(f"read_historical_data: 表名={table_name}, 条件={conditions}, 日期范围={start_date}至{end_date}")
        
        # 初始化条件字典
        if conditions is None:
            conditions = {}
        else:
            # 创建条件字典的副本，避免修改原始字典
            conditions = conditions.copy()
            
        # 检查表是否存在
        try:
            table_exists = self._check_table_exists(table_name)
            if not table_exists:
                logging.error(f"表 {table_name} 不存在")
                return pd.DataFrame()
        except Exception as e:
            logging.error(f"检查表 {table_name} 是否存在时出错: {e}")
            return pd.DataFrame()
        
        # 处理日期范围条件
        if start_date:
            # 确保日期是字符串格式
            if isinstance(start_date, datetime.date) or isinstance(start_date, datetime.datetime):
                start_date = start_date.strftime('%Y-%m-%d')
            conditions[date_col_name] = (">=", start_date)
        
        if end_date:
            # 确保日期是字符串格式
            if isinstance(end_date, datetime.date) or isinstance(end_date, datetime.datetime):
                end_date = end_date.strftime('%Y-%m-%d')
                
            if date_col_name in conditions:
                # 如果已经有日期条件，则需要分别添加
                conditions[f"{date_col_name}_end"] = ("<=", end_date)
            else:
                conditions[date_col_name] = ("<=", end_date)
        
        # 按日期排序
        order_by = [date_col_name]
        
        # 处理特殊的日期范围条件
        if f"{date_col_name}_end" in conditions:
            end_condition = conditions.pop(f"{date_col_name}_end")
            df = self.read_table(table_name, conditions, order_by=order_by, 
                               order_desc=order_desc, limit=limit)
            
            # 在DataFrame上再次过滤
            if not df.empty:
                # 确保日期列存在
                if date_col_name not in df.columns:
                    logging.error(f"日期列 {date_col_name} 不存在于查询结果中")
                    return df
                
                # 确保日期类型一致
                try:
                    # 将日期列转换为datetime类型
                    df[date_col_name] = pd.to_datetime(df[date_col_name])
                    
                    # 将条件值转换为datetime类型
                    end_date_value = None
                    if isinstance(end_condition[1], str):
                        end_date_value = pd.to_datetime(end_condition[1])
                    elif isinstance(end_condition[1], (datetime.date, datetime.datetime)):
                        end_date_value = pd.Timestamp(end_condition[1])
                    else:
                        end_date_value = end_condition[1]
                    
                    # 过滤数据
                    result_df = df[df[date_col_name] <= end_date_value]
                except Exception as e:
                    logging.error(f"日期过滤时出错: {e}")
                    result_df = df
            else:
                result_df = df
            logging.debug(f"read_historical_data: 返回 {len(result_df)} 条记录")
            return result_df
        else:
            result_df = self.read_table(table_name, conditions, order_by=order_by, 
                                 order_desc=order_desc, limit=limit)
            logging.debug(f"read_historical_data: 返回 {len(result_df)} 条记录")
            return result_df
    
    def read_stock_quotes(self, stock_code: str, start_date: str = None, 
                         end_date: str = None, adj_type: str = "后复权",
                         limit: int = 60) -> pd.DataFrame:
        """读取股票行情数据
        
        Args:
            stock_code (str): 股票代码
            start_date (str, optional): 开始日期，格式为'YYYY-MM-DD'
            end_date (str, optional): 结束日期，格式为'YYYY-MM-DD'
            adj_type (str, optional): 复权类型，可选值为"不复权"、"前复权"、"后复权"，默认为"后复权"
            limit (int, optional): 返回记录数量限制，默认为60
            
        Returns:
            pandas.DataFrame: 查询结果DataFrame
        """
        # 根据复权类型选择表名
        if adj_type == "后复权":
            table_name = "股票历史行情_后复权"
        elif adj_type == "前复权":
            table_name = "股票历史行情_前复权"
        else:
            table_name = "股票历史行情_不复权"
        
        # 使用通用历史数据读取方法
        return self.read_historical_data(
            table_name=table_name,
            conditions={"股票代码": stock_code},
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
    
    def read_technical_indicators(self, stock_code: str, start_date: str = None, 
                                end_date: str = None, indicators: List[str] = None,
                                limit: int = 60) -> pd.DataFrame:
        """读取股票技术指标数据
        
        Args:
            stock_code (str): 股票代码
            start_date (str, optional): 开始日期，格式为'YYYY-MM-DD'
            end_date (str, optional): 结束日期，格式为'YYYY-MM-DD'
            indicators (List[str], optional): 指标名称列表，不指定则获取所有指标
            limit (int, optional): 返回记录数量限制，默认为60
            
        Returns:
            pandas.DataFrame: 查询结果DataFrame
        """
        table_name = "股票技术指标"
        
        # 确保日期是字符串格式
        start_date_str = start_date
        if isinstance(start_date, (datetime.date, datetime.datetime)):
            start_date_str = start_date.strftime('%Y-%m-%d')
            
        end_date_str = end_date
        if isinstance(end_date, (datetime.date, datetime.datetime)):
            end_date_str = end_date.strftime('%Y-%m-%d')
        
        # 使用通用历史数据读取方法
        df = self.read_historical_data(
            table_name=table_name,
            conditions={"股票代码": stock_code},
            start_date=start_date_str,
            end_date=end_date_str,
            limit=limit
        )
        
        # 如果指定了要查询的指标列，则只保留这些列和必要的标识列
        if indicators and not df.empty:
            # 确保保留日期和股票代码列
            keep_cols = ["日期", "股票代码"] + indicators
            # 只保留存在的列
            existing_cols = [col for col in keep_cols if col in df.columns]
            df = df[existing_cols]
            
        return df
    
    def read_stock_info(self, stock_code: str = None, stock_name: str = None, 
                       industry: str = None) -> pd.DataFrame:
        """读取股票基本信息
        
        Args:
            stock_code (str, optional): 股票代码
            stock_name (str, optional): 股票名称
            industry (str, optional): 所属行业
            
        Returns:
            pandas.DataFrame: 查询结果DataFrame
        """
        table_name = "股票基本信息"
        conditions = {}
        
        if stock_code:
            conditions["股票代码"] = stock_code
        
        if stock_name:
            conditions["股票名称"] = stock_name
        
        if industry:
            conditions["所属行业"] = industry
        
        return self.read_table(table_name, conditions)
    
    def read_industry_info(self, industry_code: str = None, 
                         industry_name: str = None) -> pd.DataFrame:
        """读取行业信息
        
        Args:
            industry_code (str, optional): 行业代码
            industry_name (str, optional): 行业名称
            
        Returns:
            pandas.DataFrame: 查询结果DataFrame
        """
        table_name = "行业板块"
        conditions = {}
        
        if industry_code:
            conditions["行业代码"] = industry_code
        
        if industry_name:
            conditions["行业名称"] = industry_name
        
        return self.read_table(table_name, conditions)
    
    def read_concept_info(self, concept_code: str = None, 
                        concept_name: str = None) -> pd.DataFrame:
        """读取概念信息
        
        Args:
            concept_code (str, optional): 概念代码
            concept_name (str, optional): 概念名称
            
        Returns:
            pandas.DataFrame: 查询结果DataFrame
        """
        table_name = "概念板块"
        conditions = {}
        
        if concept_code:
            conditions["概念代码"] = concept_code
        
        if concept_name:
            conditions["概念名称"] = concept_name
        
        return self.read_table(table_name, conditions)
    
    def read_index_quotes(self, index_code: str, start_date: str = None, 
                         end_date: str = None, limit: int = 60) -> pd.DataFrame:
        """读取指数行情数据
        
        Args:
            index_code (str): 指数代码
            start_date (str, optional): 开始日期，格式为'YYYY-MM-DD'
            end_date (str, optional): 结束日期，格式为'YYYY-MM-DD'
            limit (int, optional): 返回记录数量限制，默认为60
            
        Returns:
            pandas.DataFrame: 查询结果DataFrame
        """
        table_name = "指数历史行情"
        
        # 使用通用历史数据读取方法
        return self.read_historical_data(
            table_name=table_name,
            conditions={"指数代码": index_code},
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
    
    def read_dragon_tiger_list(self, stock_code: str = None, 
                             trade_date: str = None, 
                             limit: int = 50) -> pd.DataFrame:
        """读取龙虎榜数据
        
        Args:
            stock_code (str, optional): 股票代码
            trade_date (str, optional): 交易日期，格式为'YYYY-MM-DD'
            limit (int, optional): 返回记录数量限制，默认为50
            
        Returns:
            pandas.DataFrame: 查询结果DataFrame
        """
        table_name = "龙虎榜详情"
        conditions = {}
        
        if stock_code:
            conditions["股票代码"] = stock_code
        
        if trade_date:
            conditions["交易日期"] = trade_date
        
        # 按日期降序排序
        order_by = ["交易日期"]
        order_desc = True
        
        return self.read_table(table_name, conditions, order_by=order_by, 
                             order_desc=order_desc, limit=limit)
    
    def read_stock_listing_stats(self, stock_code: str) -> pd.DataFrame:
        """读取个股上榜统计
        
        Args:
            stock_code (str): 股票代码
            
        Returns:
            pandas.DataFrame: 查询结果DataFrame
        """
        table_name = "个股上榜统计"
        conditions = {"股票代码": stock_code}
        
        return self.read_table(table_name, conditions)
    
    def close(self):
        """关闭数据库连接"""
        if self.db:
            self.db.close()
            logger.info("表数据读取器已关闭数据库连接")


# 测试代码
if __name__ == "__main__":
    # 创建表数据读取器实例，启用调试模式
    reader = TableDataReader(debug_mode=True)
    
    # 测试读取股票基本信息
    stock_info = reader.read_stock_info(stock_code="000001")
    print("\n股票基本信息:")
    print(stock_info)
    
    # 测试读取财务报表数据
    balance_sheet = reader.read_financial_statement("资产负债表", "000001")
    print("\n资产负债表:")
    print(balance_sheet)
    
    # 测试读取股票行情数据
    quotes = reader.read_stock_quotes("000001", limit=10)
    print("\n股票行情数据:")
    print(quotes)
    
    # 测试读取技术指标数据
    indicators = reader.read_technical_indicators("000001", indicators=["SMA5", "SMA10", "RSI6"], limit=10)
    print("\n技术指标数据:")
    print(indicators)
    
    # 关闭数据库连接
    reader.close()