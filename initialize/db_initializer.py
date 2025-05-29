#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库初始化脚本

该脚本用于初始化PostgreSQL数据库，执行tables.sql文件创建所有必要的表结构。
"""

import os
import sys
import argparse
from pathlib import Path
import psycopg2

# 将项目根目录添加到系统路径，以便导入自定义模块
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.logger import LoggerManager
from db.postgresql_manager import PostgreSQLManager

# 初始化日志
logger_manager = LoggerManager()
logger = logger_manager.get_logger("db_initializer")

# SQL文件路径
SQL_FILE = Path(project_root) / "initialize" / "tables.sql"


def create_database():
    """创建数据库
    
    由于CREATE DATABASE不能在事务块内执行，需要单独连接到默认数据库执行
    
    Returns:
        bool: 创建是否成功
    """
    try:
        # 加载配置
        config_path = os.path.join(project_root, 'config', 'connection.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            import yaml
            config = yaml.safe_load(f)
        
        db_config = config['postgresql']
        
        # 连接到默认的postgres数据库
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database='postgres',  # 连接到默认数据库
            user=db_config['user'],
            password=db_config['password']
        )
        conn.autocommit = True  # 设置自动提交，CREATE DATABASE需要在自动提交模式下执行
        
        with conn.cursor() as cursor:
            # 检查数据库是否已存在
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_config['database'],))
            exists = cursor.fetchone()
            
            if not exists:
                # 创建数据库
                cursor.execute(f"CREATE DATABASE {db_config['database']} WITH ENCODING 'UTF8' LC_COLLATE 'zh-Hans' LC_CTYPE 'zh-Hans' LOCALE_PROVIDER 'libc' TEMPLATE template0;")
                logger.info(f"数据库 {db_config['database']} 创建成功")
            else:
                logger.info(f"数据库 {db_config['database']} 已存在")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"创建数据库失败: {e}")
        return False


def execute_sql_file(cursor, file_path):
    """执行SQL文件中的表创建语句
    
    Args:
        cursor: 数据库游标
        file_path (Path): SQL文件路径
        
    Returns:
        bool: 执行是否成功
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割SQL语句，跳过CREATE DATABASE语句
        sql_statements = []
        current_statement = ""
        
        # 按行处理，处理多行语句和注释
        for line in sql_content.splitlines():
            line = line.strip()
            
            # 跳过空行和注释行
            if not line or line.startswith('--'):
                continue
                
            current_statement += line + " "
            
            # 如果行以分号结束，说明一条语句结束
            if line.endswith(';'):
                # 跳过CREATE DATABASE语句
                if not current_statement.upper().strip().startswith('CREATE DATABASE'):
                    sql_statements.append(current_statement)
                current_statement = ""
        
        # 执行所有有效的SQL语句
        for statement in sql_statements:
            if statement.strip():
                logger.info(f"执行SQL语句: {statement[:50]}...")
                cursor.execute(statement)
        
        logger.info(f"成功执行SQL文件: {file_path.name}")
        return True
    except psycopg2.Error as e:
        logger.error(f"执行SQL文件 {file_path.name} 失败: {e}")
        logger.error(f"错误详情: {e.pgcode} - {e.pgerror}")
        return False
    except Exception as e:
        logger.error(f"执行SQL文件 {file_path.name} 时发生意外错误: {e}")
        return False


def initialize_database():
    """初始化数据库"""
    logger.info("开始初始化数据库...")
    
    # 检查SQL文件是否存在
    if not SQL_FILE.exists():
        logger.error(f"SQL文件 {SQL_FILE} 不存在，请确保tables.sql已复制到initialize目录。")
        return False
    
    # 首先创建数据库
    if not create_database():
        logger.error("创建数据库失败，初始化过程终止。")
        return False
    
    # 初始化数据库连接
    try:
        db_manager = PostgreSQLManager()
        if not db_manager.conn:  # 检查连接是否成功建立
            logger.error("无法连接到数据库，请检查配置和数据库服务状态。")
            return False
    except Exception as e:
        logger.error(f"初始化数据库管理器失败: {e}")
        return False
    
    success = False
    try:
        # 使用数据库连接执行SQL文件
        with db_manager.conn.cursor() as cursor:
            if execute_sql_file(cursor, SQL_FILE):
                db_manager.conn.commit()
                logger.info("数据库表结构初始化成功。")
                success = True
            else:
                db_manager.conn.rollback()
                logger.error("数据库表结构初始化失败，已回滚更改。")
    except Exception as e:
        logger.error(f"执行数据库初始化过程中发生错误: {e}")
        if db_manager.conn:
            db_manager.conn.rollback()
    finally:
        if db_manager:
            db_manager.close()
            logger.info("数据库连接已关闭。")
    
    return success


def main():
    parser = argparse.ArgumentParser(description="PostgreSQL数据库初始化工具")
    parser.add_argument(
        "--force", 
        action="store_true",
        help="强制执行初始化，即使数据库已存在也会重新创建表结构"
    )
    
    args = parser.parse_args()
    
    # 执行数据库初始化
    if initialize_database():
        logger.info("数据库初始化完成。")
        sys.exit(0)
    else:
        logger.error("数据库初始化失败。")
        sys.exit(1)


if __name__ == "__main__":
    main()