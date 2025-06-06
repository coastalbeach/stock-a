#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
增强版PostgreSQL数据库管理器

扩展基本PostgreSQL管理器，集成触发器、存储过程、函数等高级功能
"""

import os
import sys
import json
import select
from pathlib import Path
import psycopg2
import psycopg2.extras
import pandas as pd

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent)  # db/enhanced_postgresql_manager.py -> stock-a
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入基本PostgreSQL管理器
from db.postgresql_manager import PostgreSQLManager


class EnhancedPostgreSQLManager(PostgreSQLManager):
    """增强版PostgreSQL数据库管理器类
    
    扩展基本PostgreSQL管理器，提供对触发器、存储过程、函数等高级功能的支持
    """
    
    def __init__(self):
        """初始化数据库连接"""
        super().__init__()
        self._setup_notification_listener()
    
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