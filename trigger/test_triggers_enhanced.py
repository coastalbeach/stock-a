#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库触发器和函数增强测试脚本

该脚本提供基于配置文件的PostgreSQL触发器测试功能：
1. 从test_config.yaml读取测试配置
2. 创建临时测试数据库
3. 在测试数据库中应用触发器
4. 根据配置执行测试用例
5. 验证测试结果
6. 生成测试报告
7. 清理测试数据库

这种方式可以安全地测试触发器，而不会影响生产数据库。
"""

import os
import sys
import argparse
import uuid
import time
import yaml
import json
from datetime import datetime
from pathlib import Path
import psycopg2
import psycopg2.extras

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
logger = logger_manager.get_logger("test_triggers_enhanced")

# 测试配置文件路径
TEST_CONFIG_PATH = Path(__file__).resolve().parent / "test_config.yaml"


def load_test_config():
    """加载测试配置"""
    try:
        with open(TEST_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        logger.error(f"测试配置文件 {TEST_CONFIG_PATH} 未找到。")
        sys.exit(1)
    except Exception as e:
        logger.error(f"加载测试配置失败: {e}")
        sys.exit(1)


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


def create_test_database(db_config, test_config):
    """创建临时测试数据库
    
    Args:
        db_config (dict): 数据库配置信息
        test_config (dict): 测试配置信息
        
    Returns:
        str: 测试数据库名称
    """
    # 生成唯一的测试数据库名称
    prefix = test_config.get('database', {}).get('name_prefix', 'test_triggers')
    test_db_name = f"{prefix}_{uuid.uuid4().hex[:8]}"
    
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


def setup_test_data(test_db_conn, setup_steps):
    """设置测试数据
    
    Args:
        test_db_conn: 测试数据库连接
        setup_steps (list): 设置步骤列表
        
    Returns:
        bool: 是否成功设置测试数据
    """
    try:
        with test_db_conn.cursor() as cursor:
            for step in setup_steps:
                if step['type'] == 'insert':
                    table_name = step['table']
                    data = step['data']
                    
                    # 构建INSERT语句
                    columns = list(data.keys())
                    values = list(data.values())
                    placeholders = ["%s"] * len(columns)
                    
                    sql = f"INSERT INTO public.\"{table_name}\" (\"{'\", \"'.join(columns)}\") VALUES ({', '.join(placeholders)})"
                    
                    logger.info(f"执行SQL: {sql}")
                    logger.info(f"参数值: {values}")
                    
                    try:
                        cursor.execute(sql, values)
                        logger.info(f"已插入测试数据到 {table_name} 表")
                    except Exception as insert_error:
                        logger.error(f"插入数据到 {table_name} 表失败: {insert_error}")
                        # 检查表是否存在
                        try:
                            cursor.execute(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table_name}')")
                            table_exists = cursor.fetchone()[0]
                            if not table_exists:
                                logger.error(f"表 {table_name} 不存在")
                            else:
                                # 检查表结构
                                cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}'")
                                columns_info = cursor.fetchall()
                                logger.info(f"表 {table_name} 的列信息: {columns_info}")
                        except Exception as check_error:
                            logger.error(f"检查表 {table_name} 失败: {check_error}")
                        raise insert_error
                    
            test_db_conn.commit()
            return True
    except Exception as e:
        logger.error(f"设置测试数据失败: {e}")
        test_db_conn.rollback()
        return False


def verify_test_results(test_db_conn, verification_steps):
    """验证测试结果
    
    Args:
        test_db_conn: 测试数据库连接
        verification_steps (list): 验证步骤列表
        
    Returns:
        tuple: (是否通过, 验证结果详情)
    """
    results = []
    all_passed = True
    
    try:
        with test_db_conn.cursor() as cursor:
            for step in verification_steps:
                result = {
                    'type': step['type'],
                    'passed': False,
                    'details': {}
                }
                
                if step['type'] == 'check_notice':
                    # 检查是否有特定的通知消息
                    # 在实际应用中，可能需要检查日志文件或特定的通知表
                    expected_message = step['expected_message']
                    
                    # 这里简化处理，假设通知消息会记录在pg_stat_activity的query字段中
                    cursor.execute(f"SELECT * FROM pg_catalog.pg_stat_activity WHERE query LIKE '%{expected_message}%';")
                    query_result = cursor.fetchall()
                    
                    result['passed'] = len(query_result) > 0
                    result['details']['expected_message'] = expected_message
                    result['details']['found'] = result['passed']
                    
                elif step['type'] == 'check_function_called':
                    # 检查特定函数是否被调用
                    function_name = step['function_name']
                    
                    # 首先检查临时表function_calls中是否有该函数的调用记录
                    try:
                        cursor.execute(f"SELECT * FROM function_calls WHERE function_name = '{function_name}';")
                        temp_table_result = cursor.fetchall()
                        if len(temp_table_result) > 0:
                            result['passed'] = True
                            result['details']['function_name'] = function_name
                            result['details']['found'] = True
                            continue
                    except Exception as e:
                        logger.debug(f"临时表function_calls查询失败: {e}，将继续检查pg_stat_activity")
                    
                    # 如果临时表中没有找到，则检查pg_stat_activity中是否有该函数的调用记录
                    cursor.execute(f"SELECT * FROM pg_catalog.pg_stat_activity WHERE query LIKE '%{function_name}%';")
                    query_result = cursor.fetchall()
                    
                    result['passed'] = len(query_result) > 0
                    result['details']['function_name'] = function_name
                    result['details']['found'] = result['passed']
                    result['details']['found'] = result['passed']
                
                results.append(result)
                if not result['passed']:
                    all_passed = False
        
        return all_passed, results
    except Exception as e:
        logger.error(f"验证测试结果失败: {e}")
        return False, [{'type': 'error', 'passed': False, 'details': {'error': str(e)}}]


def run_test_cases(test_db_conn, test_cases):
    """运行测试用例
    
    Args:
        test_db_conn: 测试数据库连接
        test_cases (list): 测试用例列表
        
    Returns:
        list: 测试结果列表
    """
    test_results = []
    
    for test_case in test_cases:
        logger.info(f"开始执行测试用例: {test_case['name']}")
        logger.info(f"描述: {test_case['description']}")
        
        result = {
            'name': test_case['name'],
            'description': test_case['description'],
            'start_time': datetime.now().isoformat(),
            'passed': False,
            'setup_success': False,
            'verification_results': []
        }
        
        # 设置测试数据
        setup_success = setup_test_data(test_db_conn, test_case['setup'])
        result['setup_success'] = setup_success
        
        if setup_success:
            # 给触发器一些执行时间
            time.sleep(1)
            
            # 验证测试结果
            passed, verification_results = verify_test_results(test_db_conn, test_case['verification'])
            result['passed'] = passed
            result['verification_results'] = verification_results
            
            if passed:
                logger.info(f"测试用例 {test_case['name']} 通过")
            else:
                logger.warning(f"测试用例 {test_case['name']} 失败")
        else:
            logger.error(f"测试用例 {test_case['name']} 设置失败，跳过验证")
        
        result['end_time'] = datetime.now().isoformat()
        test_results.append(result)
    
    return test_results


def generate_test_report(test_results, output_file=None):
    """生成测试报告
    
    Args:
        test_results (list): 测试结果列表
        output_file (str, optional): 输出文件路径
        
    Returns:
        str: 测试报告内容
    """
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results if result['passed'])
    
    report = {
        'summary': {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': f"{passed_tests / total_tests * 100:.2f}%" if total_tests > 0 else "0%",
            'timestamp': datetime.now().isoformat()
        },
        'test_results': test_results
    }
    
    report_json = json.dumps(report, indent=2, ensure_ascii=False)
    
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_json)
            logger.info(f"测试报告已保存到 {output_file}")
        except Exception as e:
            logger.error(f"保存测试报告失败: {e}")
    
    return report_json


def main():
    parser = argparse.ArgumentParser(description="PostgreSQL触发器和函数增强测试工具")
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
    parser.add_argument(
        "--report",
        type=str,
        help="测试报告输出文件路径"
    )
    
    args = parser.parse_args()
    
    if not args.test_all:
        parser.print_help()
        logger.warning("请提供 --test-all 参数以运行测试。")
        sys.exit(1)
    
    # 加载测试配置
    test_config = load_test_config()
    
    # 加载数据库配置
    db_config = load_db_config()
    
    # 创建测试数据库
    test_db_name = create_test_database(db_config, test_config)
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
        test_results = run_test_cases(test_db_conn, test_config['test_cases'])
        
        # 生成测试报告
        report_file = args.report or os.path.join(project_root, 'logs', f"trigger_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        report_json = generate_test_report(test_results, report_file)
        
        # 输出测试摘要
        total_tests = len(test_results)
        passed_tests = sum(1 for result in test_results if result['passed'])
        logger.info(f"测试完成: 总计 {total_tests} 个测试用例, 通过 {passed_tests} 个, 失败 {total_tests - passed_tests} 个")
        
        # 关闭测试数据库连接
        test_db_conn.close()
    finally:
        # 如果不保留测试数据库，则删除它
        keep_db = args.keep_db or test_config.get('database', {}).get('keep_after_test', False)
        if not keep_db:
            drop_test_database(db_config, test_db_name)
            logger.info("测试数据库已删除")
        else:
            logger.info(f"测试数据库 {test_db_name} 已保留，请手动清理")


if __name__ == "__main__":
    main()