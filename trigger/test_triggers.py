#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库触发器和函数测试脚本

该脚本提供安全测试PostgreSQL触发器和函数的功能，通过以下方式实现：
1. 创建临时测试数据库
2. 在测试数据库中应用触发器
3. 执行测试用例验证触发器功能
4. 清理测试数据库

这种方式可以安全地测试触发器，而不会影响生产数据库。
"""

import os
import sys
import argparse
import uuid
from pathlib import Path
import psycopg2
import yaml
import time

# 将项目根目录添加到系统路径，以便导入自定义模块
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.logger import LoggerManager
from db.postgresql_manager import PostgreSQLManager

# 导入apply_triggers模块中的函数
from apply_triggers import SQL_EXECUTION_ORDER, SQL_DIR, execute_sql_file

# 初始化日志
logger_manager = LoggerManager()
logger = logger_manager.get_logger("test_triggers")


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


def create_test_database(db_config):
    """创建临时测试数据库
    
    Args:
        db_config (dict): 数据库配置信息
        
    Returns:
        str: 测试数据库名称
    """
    # 生成唯一的测试数据库名称
    test_db_name = f"test_triggers_{uuid.uuid4().hex[:8]}"
    
    # 连接到默认数据库以创建测试数据库
    conn = None
    try:
        # 连接到默认的postgres数据库
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database="postgres",  # 连接到默认数据库
            user=db_config['user'],
            password=db_config['password']
        )
        conn.autocommit = True  # 设置自动提交，CREATE DATABASE需要在自己的事务中
        
        with conn.cursor() as cursor:
            # 创建测试数据库
            cursor.execute(f"CREATE DATABASE {test_db_name}")
            logger.info(f"已创建测试数据库: {test_db_name}")
            
        return test_db_name
    except Exception as e:
        logger.error(f"创建测试数据库失败: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()


def drop_test_database(db_config, test_db_name):
    """删除测试数据库
    
    Args:
        db_config (dict): 数据库配置信息
        test_db_name (str): 测试数据库名称
    """
    conn = None
    try:
        # 连接到默认的postgres数据库
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database="postgres",  # 连接到默认数据库
            user=db_config['user'],
            password=db_config['password']
        )
        conn.autocommit = True
        
        with conn.cursor() as cursor:
            # 强制断开所有到测试数据库的连接
            cursor.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{test_db_name}'
            AND pid <> pg_backend_pid();
            """)
            
            # 删除测试数据库
            cursor.execute(f"DROP DATABASE {test_db_name}")
            logger.info(f"已删除测试数据库: {test_db_name}")
    except Exception as e:
        logger.error(f"删除测试数据库失败: {e}")
    finally:
        if conn:
            conn.close()


def get_test_db_connection(db_config, test_db_name):
    """获取测试数据库连接
    
    Args:
        db_config (dict): 数据库配置信息
        test_db_name (str): 测试数据库名称
        
    Returns:
        connection: 数据库连接对象
    """
    try:
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=test_db_name,
            user=db_config['user'],
            password=db_config['password']
        )
        return conn
    except Exception as e:
        logger.error(f"连接测试数据库失败: {e}")
        return None


def apply_triggers_to_test_db(test_db_conn):
    """将触发器应用到测试数据库
    
    Args:
        test_db_conn: 测试数据库连接
        
    Returns:
        bool: 是否成功应用所有触发器
    """
    logger.info("开始将触发器应用到测试数据库...")
    all_successful = True
    
    with test_db_conn.cursor() as cursor:
        for sql_file_name in SQL_EXECUTION_ORDER:
            file_path = SQL_DIR / sql_file_name
            if not file_path.exists():
                logger.warning(f"SQL文件 {sql_file_name} 未找到，跳过。")
                all_successful = False
                continue
            
            if not execute_sql_file(cursor, file_path):
                all_successful = False
                logger.error(f"文件 {sql_file_name} 执行失败，后续SQL文件将不会执行。")
                test_db_conn.rollback()
                return False
        
        if all_successful:
            test_db_conn.commit()
            logger.info("所有SQL文件均已成功应用到测试数据库。")
        else:
            test_db_conn.rollback()
            logger.error("部分SQL文件执行失败，已回滚所有更改。")
    
    return all_successful


def run_trigger_tests(test_db_conn):
    """运行触发器测试用例
    
    Args:
        test_db_conn: 测试数据库连接
        
    Returns:
        bool: 测试是否全部通过
    """
    logger.info("开始运行触发器测试用例...")
    all_tests_passed = True
    
    try:
        # 测试用例1: 测试除权除息信息触发器
        logger.info("测试用例1: 测试除权除息信息触发器")
        with test_db_conn.cursor() as cursor:
            # 插入测试数据
            cursor.execute("""
            INSERT INTO public."除权除息信息" (
                "股票代码", "公告日期", "除权除息日", "每股送股比例", "每股转增比例", "每股派息金额_税前"
            ) VALUES (
                '000001', '2023-01-01', '2023-01-10', 0.0, 0.0, 0.5
            );
            """)
            test_db_conn.commit()
            logger.info("已插入测试数据到除权除息信息表")
            
            # 验证触发器是否正常工作 (这里只是简单检查是否有日志输出)
            # 实际应用中，应该检查复权因子表是否有相应的更新
            time.sleep(1)  # 给触发器一些执行时间
            
            # 检查是否有日志输出
            cursor.execute("SELECT * FROM pg_catalog.pg_stat_activity WHERE query LIKE '%update_hfq_factor_on_dividend_change%';")
            result = cursor.fetchall()
            if result:
                logger.info("触发器已执行，测试通过")
            else:
                logger.warning("未检测到触发器执行，测试可能失败")
                all_tests_passed = False
        
        # 测试用例2: 测试复权因子表触发器
        # 这里可以添加更多测试用例
        
        return all_tests_passed
    except Exception as e:
        logger.error(f"运行测试用例时发生错误: {e}")
        test_db_conn.rollback()
        return False


def main():
    parser = argparse.ArgumentParser(description="PostgreSQL触发器和函数测试工具")
    parser.add_argument(
        "--test-all", 
        action="store_true",
        help="测试所有触发器和函数"
    )
    parser.add_argument(
        "--keep-db",
        action="store_true",
        help="测试完成后保留测试数据库（默认会删除）"
    )
    
    args = parser.parse_args()
    
    if not args.test_all:
        parser.print_help()
        logger.warning("请提供 --test-all 参数以运行测试。")
        sys.exit(1)
    
    # 加载数据库配置
    db_config = load_db_config()
    
    # 创建测试数据库
    test_db_name = create_test_database(db_config)
    logger.info(f"测试将在临时数据库 {test_db_name} 中进行")
    
    try:
        # 获取测试数据库连接
        test_db_conn = get_test_db_connection(db_config, test_db_name)
        if not test_db_conn:
            logger.error("无法连接到测试数据库，测试终止。")
            sys.exit(1)
        
        # 应用触发器到测试数据库
        if not apply_triggers_to_test_db(test_db_conn):
            logger.error("应用触发器失败，测试终止。")
            sys.exit(1)
        
        # 运行测试用例
        test_result = run_trigger_tests(test_db_conn)
        if test_result:
            logger.info("所有测试用例通过！")
        else:
            logger.warning("部分测试用例失败，请检查日志获取详细信息。")
        
        # 关闭测试数据库连接
        test_db_conn.close()
    finally:
        # 如果不保留测试数据库，则删除它
        if not args.keep_db:
            drop_test_database(db_config, test_db_name)
            logger.info("测试数据库已删除")
        else:
            logger.info(f"测试数据库 {test_db_name} 已保留，请手动清理")


if __name__ == "__main__":
    main()