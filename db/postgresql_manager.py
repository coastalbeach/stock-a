#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PostgreSQL数据库管理器

管理PostgreSQL连接和操作，适用于存储结构化历史数据、财务报表、公司信息等需要关系查询的数据
"""

import os
import sys
import yaml
import psycopg2
import psycopg2.extras
import pandas as pd
from pathlib import Path
from queue import Queue
import threading
from contextlib import contextmanager

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent)  # db/postgresql_manager.py -> stock-a
if project_root not in sys.path:
    sys.path.append(project_root)


class DatabasePool:
    """数据库连接池类
    
    提供数据库连接池功能，支持多线程并发访问
    """
    
    def __init__(self, max_connections=8):
        """初始化连接池
        
        Args:
            max_connections (int): 最大连接数
        """
        self.max_connections = max_connections
        self.connections = Queue(maxsize=max_connections)
        self.config = self._load_config()
        self.lock = threading.Lock()
        self._init_pool()
        
    def _load_config(self):
        """加载数据库配置"""
        config_path = os.path.join(project_root, 'config', 'connection.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
        
    def _init_pool(self):
        """初始化连接池"""
        for _ in range(self.max_connections):
            conn = self._create_connection()
            if conn:
                self.connections.put(conn)
                
    def _create_connection(self):
        """创建数据库连接"""
        try:
            db_config = self.config['postgresql']
            conn = psycopg2.connect(
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['database'],
                user=db_config['user'],
                password=db_config['password']
            )
            return conn
        except Exception as e:
            print(f"创建数据库连接失败: {e}")
            return None
            
    def get_connection(self):
        """获取连接"""
        return self.connections.get()
        
    def return_connection(self, conn):
        """归还连接"""
        if conn and not conn.closed:
            self.connections.put(conn)
        else:
            # 连接已关闭，创建新连接
            new_conn = self._create_connection()
            if new_conn:
                self.connections.put(new_conn)
                
    @contextmanager
    def get_connection_context(self):
        """获取连接的上下文管理器
        
        使用方式:
        with pool.get_connection_context() as conn:
            cursor = conn.cursor()
            # 执行数据库操作
        """
        conn = self.get_connection()
        try:
            yield conn
        finally:
            self.return_connection(conn)
                
    def close_all(self):
        """关闭所有连接"""
        while not self.connections.empty():
            conn = self.connections.get()
            if conn and not conn.closed:
                conn.close()


class PostgreSQLManager:
    """PostgreSQL数据库管理器类
    
    提供PostgreSQL数据库连接和操作功能，支持数据版本管理、历史追溯和复杂SQL查询
    现在支持连接池模式和单连接模式
    """
    
    def __init__(self, use_pool=False, max_connections=8):
        """初始化数据库连接
        
        Args:
            use_pool (bool): 是否使用连接池模式
            max_connections (int): 连接池最大连接数（仅在use_pool=True时有效）
        """
        self.use_pool = use_pool
        self.config = self._load_config()
        
        if use_pool:
            self.pool = DatabasePool(max_connections)
            self.conn = None
            self.cursor = None
        else:
            self.pool = None
            self.conn = None
            self.cursor = None
            self.connect()
    
    def _load_config(self):
        """加载数据库配置"""
        config_path = os.path.join(project_root, 'config', 'connection.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    
    def connect(self):
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
            print("PostgreSQL数据库连接成功")
            return True
        except Exception as e:
            print(f"PostgreSQL数据库连接失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.use_pool:
            if self.pool:
                self.pool.close_all()
                print("PostgreSQL连接池已关闭")
        else:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
            print("PostgreSQL数据库连接已关闭")
    
    def execute(self, sql, params=None):
        """执行SQL语句
        
        Args:
            sql (str): SQL语句
            params (tuple, optional): SQL参数
            
        Returns:
            bool: 执行是否成功
        """
        if self.use_pool:
            return self._execute_with_pool(sql, params)
        else:
            return self._execute_single(sql, params)
    
    def _execute_single(self, sql, params=None):
        """单连接模式执行SQL"""
        try:
            if params:
                self.cursor.execute(sql, params)
            else:
                self.cursor.execute(sql)
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"执行SQL失败: {e}\nSQL: {sql}\n参数: {params}")
            return False
    
    def _execute_with_pool(self, sql, params=None):
        """连接池模式执行SQL"""
        with self.pool.get_connection_context() as conn:
            try:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                conn.rollback()
                print(f"执行SQL失败: {e}\nSQL: {sql}\n参数: {params}")
                return False
    
    def query(self, sql, params=None):
        """查询数据
        
        Args:
            sql (str): SQL查询语句
            params (tuple, optional): SQL参数
            
        Returns:
            list: 查询结果列表
        """
        if self.use_pool:
            return self._query_with_pool(sql, params)
        else:
            return self._query_single(sql, params)
    
    def _query_single(self, sql, params=None):
        """单连接模式查询数据"""
        try:
            if params:
                self.cursor.execute(sql, params)
            else:
                self.cursor.execute(sql)
            return self.cursor.fetchall()
        except Exception as e:
            self.conn.rollback()  # 回滚事务，避免事务中断状态
            #print(f"查询数据失败: {e}\nSQL: {sql}\n参数: {params}")
            return []
    
    def _query_with_pool(self, sql, params=None):
        """连接池模式查询数据"""
        with self.pool.get_connection_context() as conn:
            try:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                result = cursor.fetchall()
                cursor.close()
                return result
            except Exception as e:
                conn.rollback()  # 回滚事务，避免事务中断状态
                #print(f"查询数据失败: {e}\nSQL: {sql}\n参数: {params}")
                return []
    
    def query_df(self, sql, params=None):
        """查询数据并返回DataFrame
        
        Args:
            sql (str): SQL查询语句
            params (tuple, optional): SQL参数
            
        Returns:
            pandas.DataFrame: 查询结果DataFrame
        """
        try:
            if params:
                self.cursor.execute(sql, params)
            else:
                self.cursor.execute(sql)
            columns = [desc[0] for desc in self.cursor.description]
            return pd.DataFrame(self.cursor.fetchall(), columns=columns)
        except Exception as e:
            self.conn.rollback()  # 回滚事务，避免事务中断状态
            print(f"查询数据失败: {e}\nSQL: {sql}\n参数: {params}")
            return pd.DataFrame()
    
    def create_table(self, table_name, columns):
        """创建数据表
        
        Args:
            table_name (str): 表名
            columns (dict): 列定义字典，格式为 {列名: 列类型}
                           特殊键 "PRIMARY KEY" 用于定义主键
            
        Returns:
            bool: 创建是否成功
        """
        try:
            # 提取主键定义
            primary_key = None
            if "PRIMARY KEY" in columns:
                primary_key = columns.pop("PRIMARY KEY")
            
            # 构建列定义
            column_defs = [f'"{col}" {dtype}' for col, dtype in columns.items()]
            
            # 如果有主键，添加主键约束
            if primary_key:
                column_defs.append(f'PRIMARY KEY ({primary_key})')
            
            # 创建表SQL
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS "{table_name}" (
                {', '.join(column_defs)}
            );
            """
            
            # 执行SQL
            self.cursor.execute(create_table_sql)
            self.conn.commit()
            print(f"表 {table_name} 创建成功")
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"创建表 {table_name} 失败: {e}")
            return False
    
    def create_index(self, table_name, index_name, columns, unique=False):
        """创建索引
        
        Args:
            table_name (str): 表名
            index_name (str): 索引名
            columns (list): 索引列名列表
            unique (bool, optional): 是否为唯一索引
            
        Returns:
            bool: 创建是否成功
        """
        try:
            # 构建索引类型
            index_type = "UNIQUE" if unique else ""
            
            # 创建索引SQL
            create_index_sql = f"""
            CREATE {index_type} INDEX IF NOT EXISTS "{index_name}" 
            ON "{table_name}" ("{'", "'.join(columns)}");
            """
            
            # 执行SQL
            self.cursor.execute(create_index_sql)
            self.conn.commit()
            print(f"索引 {index_name} 创建成功")
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"创建索引 {index_name} 失败: {e}")
            return False
    
    def insert_df(self, table_name, df, conflict_columns=None, update_columns=None):
        """将DataFrame插入数据表
        
        Args:
            table_name (str): 表名
            df (pandas.DataFrame): 数据DataFrame
            conflict_columns (list, optional): 冲突检查列名列表
            update_columns (list, optional): 冲突时更新的列名列表
            
        Returns:
            bool: 插入是否成功
        """
        if df.empty:
            print("没有数据需要插入")
            return True
        
        if self.use_pool:
            return self._insert_df_with_pool(table_name, df, conflict_columns, update_columns)
        else:
            return self._insert_df_single(table_name, df, conflict_columns, update_columns)
    
    def _insert_df_single(self, table_name, df, conflict_columns=None, update_columns=None):
        """单连接模式插入DataFrame"""
        try:
            # 准备列名和数据
            columns = list(df.columns)
            records = df.to_dict('records')
            values = [[r[col] for col in columns] for r in records]
            
            # 构建基本插入SQL
            insert_sql = f"""
            INSERT INTO "{table_name}" ({', '.join([f'"{col}"' for col in columns])}) 
            VALUES %s
            """
            
            # 如果指定了冲突处理
            if conflict_columns and update_columns:
                # 构建冲突处理SQL
                conflict_sql = f"ON CONFLICT ({', '.join([f'"{col}"' for col in conflict_columns])}) DO UPDATE SET " + \
                               ", ".join([f'"{col}" = EXCLUDED."{col}"' for col in update_columns])
                insert_sql += conflict_sql
            
            # 执行批量插入
            psycopg2.extras.execute_values(self.cursor, insert_sql, values)
            self.conn.commit()
            #print(f"成功插入 {len(records)} 条数据到表 {table_name}")
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"插入数据到表 {table_name} 失败: {e}")
            return False
    
    def _insert_df_with_pool(self, table_name, df, conflict_columns=None, update_columns=None):
        """连接池模式插入DataFrame"""
        with self.pool.get_connection_context() as conn:
            try:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                
                # 准备列名和数据
                columns = list(df.columns)
                records = df.to_dict('records')
                values = [[r[col] for col in columns] for r in records]
                
                # 构建基本插入SQL
                insert_sql = f"""
                INSERT INTO "{table_name}" ({', '.join([f'"{col}"' for col in columns])}) 
                VALUES %s
                """
                
                # 如果指定了冲突处理
                if conflict_columns and update_columns:
                    # 构建冲突处理SQL
                    conflict_sql = f"ON CONFLICT ({', '.join([f'"{col}"' for col in conflict_columns])}) DO UPDATE SET " + \
                                   ", ".join([f'"{col}" = EXCLUDED."{col}"' for col in update_columns])
                    insert_sql += conflict_sql
                
                # 执行批量插入
                psycopg2.extras.execute_values(cursor, insert_sql, values)
                conn.commit()
                cursor.close()
                #print(f"成功插入 {len(records)} 条数据到表 {table_name}")
                return True
            except Exception as e:
                conn.rollback()
                print(f"插入数据到表 {table_name} 失败: {e}")
                return False

    def table_exists(self, table_name):
        """检查表是否存在
        
        Args:
            table_name (str): 表名
            
        Returns:
            bool: 表是否存在
        """
        try:
            self.cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            );
            """, (table_name,))
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(f"检查表 {table_name} 是否存在失败: {e}")
            return False
    
    def get_table_columns(self, table_name):
        """获取表的列名
        
        Args:
            table_name (str): 表名
            
        Returns:
            list: 列名列表
        """
        try:
            self.cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = %s
            ORDER BY ordinal_position;
            """, (table_name,))
            return [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"获取表 {table_name} 的列名失败: {e}")
            return []
    
    def query_one(self, sql, params=None):
        """查询单条数据
        
        Args:
            sql (str): SQL查询语句
            params (tuple, optional): SQL参数
            
        Returns:
            tuple: 单条查询结果，如果没有结果则返回None
        """
        if self.use_pool:
            return self._query_one_with_pool(sql, params)
        else:
            return self._query_one_single(sql, params)
    
    def _query_one_single(self, sql, params=None):
        """单连接模式查询单条数据"""
        try:
            if params:
                self.cursor.execute(sql, params)
            else:
                self.cursor.execute(sql)
            return self.cursor.fetchone()
        except Exception as e:
            self.conn.rollback()  # 回滚事务，避免事务中断状态
            print(f"查询单条数据失败: {e}\nSQL: {sql}\n参数: {params}")
            return None
    
    def _query_one_with_pool(self, sql, params=None):
        """连接池模式查询单条数据"""
        with self.pool.get_connection_context() as conn:
            try:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                result = cursor.fetchone()
                cursor.close()
                return result
            except Exception as e:
                conn.rollback()  # 回滚事务，避免事务中断状态
                print(f"查询单条数据失败: {e}\nSQL: {sql}\n参数: {params}")
                return None
    
    def upsert_from_df(self, df, table_name, primary_keys):
        """将DataFrame插入或更新到数据表（UPSERT操作）
        
        当主键冲突时，更新所有非主键列的值
        
        Args:
            df (pandas.DataFrame): 数据DataFrame
            table_name (str): 表名
            primary_keys (list): 主键列名列表
            
        Returns:
            bool: 操作是否成功
        """
        if df.empty:
            print("没有数据需要插入或更新")
            return True
        
        try:
            # 获取所有列名
            columns = list(df.columns)
            
            # 确定需要更新的列（非主键列）
            update_columns = [col for col in columns if col not in primary_keys]
            
            # 调用insert_df方法，指定冲突处理
            return self.insert_df(
                table_name=table_name,
                df=df,
                conflict_columns=primary_keys,
                update_columns=update_columns
            )
        except Exception as e:
            print(f"UPSERT操作到表 {table_name} 失败: {e}")
            return False