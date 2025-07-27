#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
增强版PostgreSQL数据库管理器

扩展基本PostgreSQL管理器，集成触发器、存储过程、函数等高级功能，
并提供统一的表数据读取接口
"""

import os
import sys
import json
import select
import logging
from pathlib import Path
import psycopg2
import psycopg2.extras
import pandas as pd
from datetime import datetime, timedelta

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent)  # db/enhanced_postgresql_manager.py -> stock-a
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入基本PostgreSQL管理器
from db.postgresql_manager import PostgreSQLManager

# 配置日志记录器
logger = logging.getLogger(__name__)


class EnhancedPostgreSQLManager(PostgreSQLManager):
    """增强版PostgreSQL数据库管理器类
    
    扩展基本PostgreSQL管理器，提供对触发器、存储过程、函数等高级功能的支持，
    并集成表数据读取功能，提供统一的数据访问接口
    """
    
    def __init__(self, debug_mode=False):
        """初始化数据库连接
        
        Args:
            debug_mode (bool, optional): 是否启用调试模式，默认为False
        """
        super().__init__()
        self._setup_notification_listener()
        
        # 表数据读取相关属性
        self.debug_mode = debug_mode
        self.tables_config = {}
        self._load_tables_config()
    
    def _setup_notification_listener(self):
        """设置数据库通知监听器"""
        try:
            # 创建一个单独的连接用于监听通知
            db_config = self.config['postgresql']
            self.notify_conn = psycopg2.connect(
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['database'],
                user=db_config['user'],
                password=db_config['password']
            )
            self.notify_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            self.notify_cursor = self.notify_conn.cursor()
            
            # 监听数据更新通知频道
            self.notify_cursor.execute("LISTEN 数据更新通知;")
            print("已设置数据库通知监听器")
        except Exception as e:
            print(f"设置数据库通知监听器失败: {e}")
            self.notify_conn = None
            self.notify_cursor = None
    
    def check_notifications(self, timeout=0):
        """检查是否有数据库通知
        
        Args:
            timeout (int, optional): 等待通知的超时时间（秒），0表示不等待
            
        Returns:
            list: 通知列表，每个通知是一个字典
        """
        if not self.notify_conn:
            return []
        
        notifications = []
        
        try:
            # 检查是否有通知
            if select.select([self.notify_conn], [], [], timeout) == ([], [], []):
                return []
            
            # 获取所有通知
            self.notify_conn.poll()
            while self.notify_conn.notifies:
                notify = self.notify_conn.notifies.pop()
                try:
                    # 解析通知内容
                    payload = json.loads(notify.payload)
                    notifications.append({
                        'channel': notify.channel,
                        'pid': notify.pid,
                        'payload': payload
                    })
                except json.JSONDecodeError:
                    notifications.append({
                        'channel': notify.channel,
                        'pid': notify.pid,
                        'payload': notify.payload
                    })
        except Exception as e:
            print(f"检查数据库通知失败: {e}")
        
        return notifications
    
    def calculate_financial_ratios(self, stock_code=None, report_date=None):
        """调用存储过程计算财务指标
        
        Args:
            stock_code (str, optional): 股票代码，不指定则计算所有股票
            report_date (str, optional): 报告期，格式为'YYYY-MM-DD'，不指定则计算所有报告期
        
        Returns:
            bool: 计算是否成功
        """
        try:
            # 构建调用存储过程的SQL
            if stock_code and report_date:
                sql = f"CALL 计算并存储财务指标('{stock_code}', '{report_date}'::DATE);"
            elif stock_code:
                sql = f"CALL 计算并存储财务指标('{stock_code}', NULL);"
            elif report_date:
                sql = f"CALL 计算并存储财务指标(NULL, '{report_date}'::DATE);"
            else:
                sql = "CALL 计算并存储财务指标(NULL, NULL);"
            
            # 执行存储过程
            return self.execute(sql)
        except Exception as e:
            print(f"计算财务指标失败: {e}")
            return False
    
    def get_financial_ratios(self, stock_code, report_date=None):
        """获取财务指标
        
        Args:
            stock_code (str): 股票代码
            report_date (str, optional): 报告期，格式为'YYYY-MM-DD'，不指定则获取最新报告期
        
        Returns:
            dict: 财务指标数据
        """
        try:
            # 构建查询SQL
            if report_date:
                sql = f"""
                SELECT * FROM "财务指标" 
                WHERE "股票代码" = '{stock_code}' AND "报告期" = '{report_date}'::DATE
                """
            else:
                sql = f"""
                SELECT * FROM "财务指标" 
                WHERE "股票代码" = '{stock_code}' 
                ORDER BY "报告期" DESC LIMIT 1
                """
            
            # 执行查询
            result = self.query_one(sql)
            
            if result:
                # 转换为字典
                columns = self.get_table_columns("财务指标")
                return {columns[i]: result[i] for i in range(len(columns))}
            else:
                print(f"未找到股票 {stock_code} 的财务指标数据")
                return {}
        except Exception as e:
            print(f"获取财务指标失败: {e}")
            return {}
    
    def get_industry_average(self, industry, report_date):
        """获取行业平均财务指标
        
        Args:
            industry (str): 行业名称
            report_date (str): 报告期，格式为'YYYY-MM-DD'
        
        Returns:
            dict: 行业平均财务指标数据
        """
        try:
            # 构建查询SQL
            sql = f"""
            SELECT * FROM 计算行业平均财务指标('{industry}', '{report_date}'::DATE)
            """
            
            # 执行查询
            result = self.query_one(sql)
            
            if result:
                # 获取列名
                self.cursor.execute(sql)
                columns = [desc[0] for desc in self.cursor.description]
                
                # 转换为字典
                return {columns[i]: result[i] for i in range(len(columns))}
            else:
                print(f"未找到行业 {industry} 在 {report_date} 的平均财务指标数据")
                return {}
        except Exception as e:
            print(f"获取行业平均财务指标失败: {e}")
            return {}
    
    def refresh_materialized_view(self, view_name="财务指标_物化视图"):
        """刷新物化视图
        
        Args:
            view_name (str, optional): 物化视图名称
            
        Returns:
            bool: 刷新是否成功
        """
        try:
            if view_name == "财务指标_物化视图":
                sql = "SELECT 刷新财务指标物化视图();"
            else:
                sql = f'REFRESH MATERIALIZED VIEW "{view_name}";'
            
            return self.execute(sql)
        except Exception as e:
            print(f"刷新物化视图 {view_name} 失败: {e}")
            return False
    
    def perform_database_maintenance(self):
        """执行数据库维护
        
        Returns:
            bool: 维护是否成功
        """
        try:
            sql = "CALL 数据库维护();"
            return self.execute(sql)
        except Exception as e:
            print(f"数据库维护失败: {e}")
            return False
    
    def get_data_version_history(self, table_name=None, record_id=None, limit=100):
        """获取数据版本历史
        
        Args:
            table_name (str, optional): 表名，不指定则获取所有表
            record_id (str, optional): 记录ID，不指定则获取所有记录
            limit (int, optional): 返回记录数量限制
        
        Returns:
            pandas.DataFrame: 数据版本历史记录DataFrame
        """
        try:
            # 构建查询条件
            conditions = []
            params = []
            
            if table_name:
                conditions.append("\"表名\" = %s")
                params.append(table_name)
            
            if record_id:
                conditions.append("\"记录ID\" = %s")
                params.append(record_id)
            
            # 构建查询SQL
            sql = "SELECT * FROM \"数据版本历史\" "
            
            if conditions:
                sql += "WHERE " + " AND ".join(conditions)
            
            sql += " ORDER BY \"操作时间\" DESC LIMIT %s"
            params.append(limit)
            
            # 执行查询并返回DataFrame
            return self.query_df(sql, tuple(params))
        except Exception as e:
            print(f"获取数据版本历史失败: {e}")
            return pd.DataFrame()
    
    def compare_data_versions(self, version_id1, version_id2=None):
        """比较两个数据版本
        
        Args:
            version_id1 (str): 第一个版本ID
            version_id2 (str, optional): 第二个版本ID，不指定则与当前数据比较
            
        Returns:
            dict: 比较结果
        """
        try:
            # 获取第一个版本的数据
            sql1 = f"SELECT * FROM \"数据版本历史\" WHERE \"版本ID\" = '{version_id1}'"
            version1 = self.query_one(sql1)
            
            if not version1:
                print(f"未找到版本ID为 {version_id1} 的数据")
                return {}
            
            # 获取表名和记录ID
            table_name = version1['表名']
            record_id = version1['记录ID']
            
            # 如果指定了第二个版本ID
            if version_id2:
                sql2 = f"SELECT * FROM \"数据版本历史\" WHERE \"版本ID\" = '{version_id2}'"
                version2 = self.query_one(sql2)
                
                if not version2:
                    print(f"未找到版本ID为 {version_id2} 的数据")
                    return {}
                
                # 比较两个版本的数据
                old_data = version1['旧数据'] if version1['旧数据'] else {}
                new_data = version2['新数据'] if version2['新数据'] else {}
            else:
                # 获取当前数据
                current_sql = f"SELECT * FROM \"{table_name}\" WHERE \"股票代码\" = '{record_id}'"
                current_data = self.query_one(current_sql)
                
                if not current_data:
                    print(f"未找到表 {table_name} 中股票代码为 {record_id} 的当前数据")
                    return {}
                
                # 转换为字典
                columns = self.get_table_columns(table_name)
                current_dict = {columns[i]: current_data[i] for i in range(len(columns))}
                
                # 比较版本数据与当前数据
                old_data = version1['旧数据'] if version1['旧数据'] else {}
                new_data = current_dict
            
            # 计算差异
            differences = {}
            all_keys = set(old_data.keys()) | set(new_data.keys())
            
            for key in all_keys:
                old_value = old_data.get(key)
                new_value = new_data.get(key)
                
                if old_value != new_value:
                    differences[key] = {
                        'old': old_value,
                        'new': new_value
                    }
            
            return {
                'version1': version_id1,
                'version2': version_id2 if version_id2 else '当前数据',
                'table': table_name,
                'record_id': record_id,
                'differences': differences
            }
        except Exception as e:
            print(f"比较数据版本失败: {e}")
            return {}
    
    def close(self):
        """关闭数据库连接"""
        # 关闭通知连接
        if hasattr(self, 'notify_cursor') and self.notify_cursor:
            self.notify_cursor.close()
        
        if hasattr(self, 'notify_conn') and self.notify_conn:
            self.notify_conn.close()
        
        # 调用父类的关闭方法
        super().close()
        logger.info("增强版PostgreSQL管理器已关闭数据库连接")
        
    # ========== 表数据读取功能 ==========
    
    def _load_tables_config(self):
        """加载表配置信息"""
        try:
            # 配置文件路径
            config_dir = os.path.join(project_root, 'config')
            tables_config_path = os.path.join(config_dir, 'tables_config.json')
            
            # 读取配置文件
            with open(tables_config_path, 'r', encoding='utf-8') as f:
                self.tables_config = json.load(f)
                
            if self.debug_mode:
                logger.debug(f"已加载表配置: {len(self.tables_config)} 个表")
        except Exception as e:
            logger.error(f"加载表配置失败: {e}")
            self.tables_config = {}
    
    def get_table_info(self, table_name):
        """获取表信息
        
        Args:
            table_name (str): 表名
            
        Returns:
            dict: 表配置信息
        """
        return self.tables_config.get(table_name, {})
    
    def get_all_table_names(self):
        """获取所有表名
        
        Returns:
            list: 表名列表
        """
        return list(self.tables_config.keys())
    
    def read_table(self, table_name, conditions=None, order_by=None, 
                  order_desc=False, limit=None, offset=None):
        """读取表数据
        
        Args:
            table_name (str): 表名
            conditions (dict, optional): 查询条件，键为列名，值为查询值
            order_by (list, optional): 排序列名列表
            order_desc (bool, optional): 是否降序排序
            limit (int, optional): 返回记录数量限制
            offset (int, optional): 返回记录起始偏移量
            
        Returns:
            pandas.DataFrame: 查询结果DataFrame
        """
        try:
            # 检查表是否存在
            if not self._check_table_exists(table_name):
                logger.warning(f"表 {table_name} 不存在")
                return pd.DataFrame()
            
            # 构建查询SQL
            sql = f'SELECT * FROM "{table_name}"'
            params = []
            
            # 添加查询条件
            if conditions:
                where_clauses = []
                for col, val in conditions.items():
                    where_clauses.append(f'"{col}" = %s')
                    params.append(val)
                
                if where_clauses:
                    sql += " WHERE " + " AND ".join(where_clauses)
            
            # 添加排序
            if order_by:
                order_clauses = [f'"{col}"' for col in order_by]
                sql += " ORDER BY " + ", ".join(order_clauses)
                
                if order_desc:
                    sql += " DESC"
            
            # 添加分页
            if limit is not None:
                sql += f" LIMIT {limit}"
                
                if offset is not None:
                    sql += f" OFFSET {offset}"
            
            # 执行查询
            if self.debug_mode:
                logger.debug(f"执行SQL: {sql}, 参数: {params}")
                
            return self.query_df(sql, tuple(params) if params else None)
        except Exception as e:
            logger.error(f"读取表 {table_name} 数据失败: {e}")
            return pd.DataFrame()
    
    def read_financial_statement(self, statement_type, stock_code=None, 
                               report_date=None, limit=4):
        """读取财务报表数据
        
        Args:
            statement_type (str): 报表类型，如'资产负债表'、'利润表'、'现金流量表'
            stock_code (str, optional): 股票代码
            report_date (str, optional): 报告期，格式为'YYYY-MM-DD'
            limit (int, optional): 返回记录数量限制，默认为4
            
        Returns:
            pandas.DataFrame: 查询结果DataFrame
        """
        try:
            # 检查表是否存在
            if not self._check_table_exists(statement_type):
                logger.warning(f"表 {statement_type} 不存在")
                return pd.DataFrame()
            
            # 构建查询条件
            conditions = {}
            if stock_code:
                conditions["股票代码"] = stock_code
                
            if report_date:
                conditions["报告期"] = report_date
            
            # 按报告期降序排序
            order_by = ["报告期"]
            order_desc = True
            
            # 执行查询
            return self.read_table(statement_type, conditions, order_by, order_desc, limit)
        except Exception as e:
            logger.error(f"读取财务报表 {statement_type} 数据失败: {e}")
            return pd.DataFrame()
    
    def _check_table_exists(self, table_name):
        """检查表是否存在
        
        Args:
            table_name (str): 表名
            
        Returns:
            bool: 表是否存在
        """
        try:
            sql = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            );
            """
            result = self.query_one(sql, (table_name,))
            return result[0] if result else False
        except Exception as e:
            logger.error(f"检查表 {table_name} 是否存在失败: {e}")
            return False
    
    def read_historical_data(self, table_name, conditions=None, 
                           start_date=None, end_date=None, limit=60):
        """读取历史数据
        
        Args:
            table_name (str): 表名
            conditions (dict, optional): 查询条件，键为列名，值为查询值
            start_date (str, optional): 开始日期，格式为'YYYY-MM-DD'
            end_date (str, optional): 结束日期，格式为'YYYY-MM-DD'
            limit (int, optional): 返回记录数量限制，默认为60
            
        Returns:
            pandas.DataFrame: 查询结果DataFrame
        """
        try:
            # 检查表是否存在
            if not self._check_table_exists(table_name):
                logger.warning(f"表 {table_name} 不存在")
                return pd.DataFrame()
            
            # 构建查询SQL
            sql = f'SELECT * FROM "{table_name}"'
            params = []
            
            # 添加查询条件
            where_clauses = []
            
            if conditions:
                for col, val in conditions.items():
                    where_clauses.append(f'"{col}" = %s')
                    params.append(val)
            
            # 添加日期范围条件
            if start_date:
                where_clauses.append('"日期" >= %s')
                params.append(start_date)
                
            if end_date:
                where_clauses.append('"日期" <= %s')
                params.append(end_date)
            
            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)
            
            # 按日期降序排序
            sql += ' ORDER BY "日期" DESC'
            
            # 添加分页
            if limit is not None:
                sql += f" LIMIT {limit}"
            
            # 执行查询
            if self.debug_mode:
                logger.debug(f"执行SQL: {sql}, 参数: {params}")
                
            df = self.query_df(sql, tuple(params) if params else None)
            
            # 如果结果不为空，按日期升序排序
            if not df.empty:
                df = df.sort_values(by="日期")
                
            return df
        except Exception as e:
            logger.error(f"读取历史数据失败: {e}")
            return pd.DataFrame()
    
    def read_stock_quotes(self, stock_code, start_date=None, end_date=None, limit=60):
        """读取股票行情数据
        
        Args:
            stock_code (str): 股票代码
            start_date (str, optional): 开始日期，格式为'YYYY-MM-DD'
            end_date (str, optional): 结束日期，格式为'YYYY-MM-DD'
            limit (int, optional): 返回记录数量限制，默认为60
            
        Returns:
            pandas.DataFrame: 查询结果DataFrame
        """
        table_name = "股票历史行情"
        
        # 处理日期参数
        if start_date is None and end_date is None:
            # 默认查询最近60个交易日数据
            end_date = datetime.now()
            start_date = end_date - timedelta(days=120)  # 考虑到非交易日，往前多取一些日期
            
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
        else:
            start_date_str = start_date
            end_date_str = end_date
        
        # 使用通用历史数据读取方法
        return self.read_historical_data(
            table_name=table_name,
            conditions={"股票代码": stock_code},
            start_date=start_date_str,
            end_date=end_date_str,
            limit=limit
        )
    
    def read_technical_indicators(self, stock_code, indicators=None, 
                                start_date=None, end_date=None, limit=60):
        """读取技术指标数据
        
        Args:
            stock_code (str): 股票代码
            indicators (list, optional): 要查询的指标列表，如['SMA5', 'SMA10', 'RSI6']
            start_date (str, optional): 开始日期，格式为'YYYY-MM-DD'
            end_date (str, optional): 结束日期，格式为'YYYY-MM-DD'
            limit (int, optional): 返回记录数量限制，默认为60
            
        Returns:
            pandas.DataFrame: 查询结果DataFrame
        """
        table_name = "技术指标"
        
        # 处理日期参数
        if start_date is None and end_date is None:
            # 默认查询最近60个交易日数据
            end_date = datetime.now()
            start_date = end_date - timedelta(days=120)  # 考虑到非交易日，往前多取一些日期
            
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
        else:
            start_date_str = start_date
            end_date_str = end_date
        
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


# 测试代码
if __name__ == "__main__":
    # 创建增强版PostgreSQL管理器实例
    db = EnhancedPostgreSQLManager()
    
    # 测试获取财务指标
    stock_code = "000001"
    ratios = db.get_financial_ratios(stock_code)
    print(f"股票 {stock_code} 的财务指标: {ratios}")
    
    # 测试获取行业平均指标
    industry = "银行"
    report_date = "2023-12-31"
    industry_avg = db.get_industry_average(industry, report_date)
    print(f"行业 {industry} 在 {report_date} 的平均指标: {industry_avg}")
    
    # 测试数据库通知
    print("等待数据库通知...")
    notifications = db.check_notifications(timeout=5)
    for notify in notifications:
        print(f"收到通知: {notify}")
    
    # 关闭数据库连接
    db.close()