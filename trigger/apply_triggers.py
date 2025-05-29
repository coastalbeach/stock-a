#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库触发器和函数统一部署脚本

该脚本用于将 `trigger/sql/` 目录下的SQL文件应用到PostgreSQL数据库中。
可以单独应用指定的SQL文件，也可以按特定顺序应用所有SQL文件。
"""

import os
import sys
import argparse
from pathlib import Path
import psycopg2
import yaml

# 将项目根目录添加到系统路径，以便导入自定义模块
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.logger import LoggerManager # 假设存在一个日志管理器
from db.postgresql_manager import PostgreSQLManager # 假设存在一个PostgreSQL管理器

# 初始化日志
logger_manager = LoggerManager()
logger = logger_manager.get_logger("apply_triggers")

# SQL文件执行顺序
# 通常是：建表 -> 创建函数 -> 创建触发器
SQL_EXECUTION_ORDER = [
    # 1. 表结构 (Tables)
    "01_tables/base_tables.sql",                 # 基础表：除权除息信息, 复权因子表
    "01_tables/stock_history_tables.sql",       # 股票历史行情表：不复权/后复权
    "01_tables/market_data_tables.sql",        # 行情数据表：周频/月频 (不复权/后复权)
    # 2. 函数 (Functions)
    "02_functions/adjustment_factor_functions.sql", # 复权因子计算、后复权价格计算函数
    "02_functions/periodic_data_functions.sql",   # 周频/月频数据计算函数 (不复权/后复权)
    # 3. 触发器 (Triggers)
    "03_triggers/adjustment_factor_triggers.sql", # 复权因子、后复权价格相关触发器
    "03_triggers/market_data_triggers.sql"      # 周频/月频数据生成相关触发器
    # 注意：不要使用根目录下的单独触发器文件，它们与03_triggers目录下的文件重复
    # trigger_on_dividend_info_change.sql
    # trigger_on_unadjusted_price_change.sql
    # trigger_on_adjustment_factor_change.sql
]

SQL_DIR = Path(__file__).resolve().parent / "sql"

def load_db_config():
    """加载数据库配置"""
    config_path = Path(project_root) / 'config' / 'connection.yaml'
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config['postgresql']
    except FileNotFoundError:
        logger.error(f"数据库配置文件 {config_path} 未找到。")
        sys.exit(1)
    except KeyError:
        logger.error(f"配置文件 {config_path} 中缺少 'postgresql' 配置节。")
        sys.exit(1)
    except Exception as e:
        logger.error(f"加载数据库配置失败: {e}")
        sys.exit(1)

def execute_sql_file(cursor, file_path):
    """执行单个SQL文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 移除可能导致问题的SQL注释（特别是行内注释）
        # PL/pgSQL中的注释有时会被psycopg2错误解析，特别是混合使用时
        # 此处简化处理，更鲁棒的方式是使用SQL解析库
        # lines = []
        # for line in sql_content.splitlines():
        #     if not line.strip().startswith('--'):
        #         lines.append(line)
        # cleaned_sql_content = "\n".join(lines)

        # psycopg2可以处理大部分情况，包括注释
        cursor.execute(sql_content)
        logger.info(f"成功执行SQL文件: {file_path.name}")
        return True
    except psycopg2.Error as e:
        logger.error(f"执行SQL文件 {file_path.name} 失败: {e}")
        logger.error(f"错误详情: {e.pgcode} - {e.pgerror}")
        # 如果需要，可以打印SQL内容以帮助调试
        # logger.debug(f"Failed SQL content:\n{sql_content}")
        return False
    except Exception as e:
        logger.error(f"执行SQL文件 {file_path.name} 时发生意外错误: {e}")
        return False

def apply_all_triggers(db_manager):
    """按顺序应用所有SQL文件"""
    logger.info("开始应用所有数据库触发器和函数...")
    all_successful = True
    conn = db_manager.conn
    if not conn:
        logger.error("数据库连接未建立，无法应用触发器。")
        return False
        
    with conn.cursor() as cursor:
        for sql_file_name in SQL_EXECUTION_ORDER:
            file_path = SQL_DIR / sql_file_name
            if not file_path.exists():
                logger.warning(f"SQL文件 {sql_file_name} 未找到，跳过。")
                all_successful = False
                continue
            
            if not execute_sql_file(cursor, file_path):
                all_successful = False
                logger.error(f"由于文件 {sql_file_name} 执行失败，后续SQL文件将不会执行。")
                conn.rollback() # 回滚当前事务
                return False # 遇到错误即停止
        
        if all_successful:
            conn.commit()
            logger.info("所有SQL文件均已成功应用。")
        else:
            conn.rollback()
            logger.error("部分SQL文件执行失败，已回滚所有更改。")
    return all_successful

def apply_single_trigger(db_manager, sql_file_name):
    """应用单个指定的SQL文件"""
    logger.info(f"开始应用SQL文件: {sql_file_name}...")
    file_path = SQL_DIR / sql_file_name
    if not file_path.exists():
        logger.error(f"SQL文件 {sql_file_name} 未找到于 {SQL_DIR}。")
        return False

    conn = db_manager.conn
    if not conn:
        logger.error("数据库连接未建立，无法应用触发器。")
        return False

    success = False
    with conn.cursor() as cursor:
        if execute_sql_file(cursor, file_path):
            conn.commit()
            logger.info(f"SQL文件 {sql_file_name} 应用成功。")
            success = True
        else:
            conn.rollback()
            logger.error(f"SQL文件 {sql_file_name} 应用失败，已回滚更改。")
    return success

def main():
    parser = argparse.ArgumentParser(description="PostgreSQL触发器和函数部署工具")
    parser.add_argument(
        "--apply", 
        type=str,
        help="指定要应用的SQL文件名 (例如, create_ex_dividend_info_table.sql)。如果为 'all'，则按顺序应用所有SQL文件。"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有可用的SQL文件及其建议的执行顺序。"
    )

    args = parser.parse_args()

    # 初始化日志
    global logger
    logger_manager = LoggerManager()
    logger = logger_manager.get_logger("apply_triggers")

    if args.list:
        logger.info("可用的SQL文件 (建议执行顺序):")
        for i, fname in enumerate(SQL_EXECUTION_ORDER):
            status = "存在" if (SQL_DIR / fname).exists() else "不存在"
            logger.info(f"{i+1}. {fname} ({status})")
        sys.exit(0)

    if not args.apply:
        parser.print_help()
        logger.warning("请提供 --apply 参数指定操作。")
        sys.exit(1)

    # 初始化数据库连接
    # 使用项目中的PostgreSQLManager
    # db_config = load_db_config()
    # db_manager = PostgreSQLManager(host=db_config['host'], 
    #                                port=db_config['port'], 
    #                                database=db_config['database'], 
    #                                user=db_config['user'], 
    #                                password=db_config['password'])
    # 假设 PostgreSQLManager 的构造函数不需要参数，或者能从配置中自动加载
    try:
        db_manager = PostgreSQLManager()
        if not db_manager.conn: # 检查连接是否成功建立
            logger.error("无法连接到数据库，请检查配置和数据库服务状态。")
            sys.exit(1)
    except Exception as e:
        logger.error(f"初始化数据库管理器失败: {e}")
        sys.exit(1)

    try:
        if args.apply.lower() == 'all':
            apply_all_triggers(db_manager)
        else:
            apply_single_trigger(db_manager, args.apply)
    finally:
        if db_manager:
            db_manager.close()
            logger.info("数据库连接已关闭。")

if __name__ == "__main__":
    main()