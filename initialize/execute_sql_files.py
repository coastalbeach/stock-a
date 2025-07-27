#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
批量执行SQL文件脚本
按照文件名顺序执行SQL文件，确保依赖关系正确

使用方法：
    python execute_sql_files.py [选项]

选项：
    --dbname 数据库名称 (默认: stocka)
    --user 用户名 (默认: postgres)
    --password 密码 (默认: 123456)
    --host 主机地址 (默认: localhost)
    --port 端口号 (默认: 5432)
    --retry 重试次数 (默认: 3)
    --help 显示帮助信息
"""

import os
import psycopg2
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

# 默认数据库连接参数
DEFAULT_DB_PARAMS = {
    'dbname': 'stocka',     # 数据库名称
    'user': 'postgres',     # 用户名
    'password': '123456',   # 密码
    'host': 'localhost',    # 主机地址
    'port': '5432'          # 端口号
}

# 最大重试次数
MAX_RETRY = 3

def execute_sql_file(conn, file_path, max_retry=MAX_RETRY):
    """
    执行单个SQL文件
    
    Args:
        conn: 数据库连接对象
        file_path: SQL文件路径
        max_retry: 最大重试次数
    """
    retry_count = 0
    while retry_count <= max_retry:
        try:
            if retry_count > 0:
                print(f"第 {retry_count} 次重试执行SQL文件: {file_path}")
            else:
                print(f"正在执行SQL文件: {file_path}")
            
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            print(f"文件大小: {file_size/1024:.2f} KB")
            
            # 记录开始时间
            start_time = time.time()
            
            # 尝试多种编码方式读取SQL文件内容
            encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin1']
            sql_content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        sql_content = f.read()
                    print(f"成功使用 {encoding} 编码读取文件")
                    break
                except UnicodeDecodeError:
                    print(f"尝试使用 {encoding} 编码读取失败，尝试下一种编码...")
                    continue
            
            if sql_content is None:
                raise Exception("无法使用已知编码读取文件，请检查文件编码")
            
            # 创建游标
            cursor = conn.cursor()
            
            # 执行SQL语句
            cursor.execute(sql_content)
            
            # 提交事务
            conn.commit()
            
            # 计算执行时间
            end_time = time.time()
            execution_time = end_time - start_time
            
            print(f"SQL文件执行成功: {file_path}")
            print(f"执行时间: {execution_time:.2f} 秒")
            return True
            
        except Exception as e:
            print(f"执行SQL文件失败: {file_path}")
            print(f"错误信息: {str(e)}")
            conn.rollback()
            
            retry_count += 1
            if retry_count <= max_retry:
                print(f"将在 3 秒后进行第 {retry_count} 次重试...")
                time.sleep(3)  # 等待3秒后重试
            else:
                print(f"已达到最大重试次数 {max_retry}，放弃执行该文件")
                return False
    
    return False

def execute_sql_files_in_directory(directory_path, db_params, max_retry=MAX_RETRY):
    """
    按顺序执行目录中的所有SQL文件
    
    Args:
        directory_path: SQL文件所在目录路径
        db_params: 数据库连接参数
        max_retry: 最大重试次数
    """
    start_total_time = time.time()
    log_file = os.path.join(directory_path, f"sql_execution_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    
    try:
        # 连接数据库
        print(f"正在连接数据库 {db_params['dbname']}@{db_params['host']}:{db_params['port']}...")
        conn = psycopg2.connect(**db_params)
        print("数据库连接成功")
        
        # 获取目录中的所有SQL文件并按名称排序
        sql_files = sorted([f for f in os.listdir(directory_path) if f.endswith('.sql')])
        
        if not sql_files:
            print(f"目录 {directory_path} 中没有找到SQL文件")
            return
        
        print(f"找到以下SQL文件: {', '.join(sql_files)}")
        print(f"总共 {len(sql_files)} 个SQL文件待执行")
        
        # 创建日志文件
        with open(log_file, 'w', encoding='utf-8') as log:
            log.write(f"SQL执行日志 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log.write(f"数据库: {db_params['dbname']}@{db_params['host']}:{db_params['port']}\n")
            log.write(f"SQL文件目录: {directory_path}\n")
            log.write(f"SQL文件列表: {', '.join(sql_files)}\n\n")
        
        # 按顺序执行SQL文件
        success_count = 0
        for i, sql_file in enumerate(sql_files):
            file_path = os.path.join(directory_path, sql_file)
            print(f"\n[{i+1}/{len(sql_files)}] 执行文件: {sql_file}")
            
            file_start_time = time.time()
            success = execute_sql_file(conn, file_path, max_retry)
            file_end_time = time.time()
            
            # 记录执行结果到日志
            with open(log_file, 'a', encoding='utf-8') as log:
                log.write(f"[{i+1}/{len(sql_files)}] {sql_file}: ")
                if success:
                    success_count += 1
                    log.write(f"成功 (耗时: {file_end_time - file_start_time:.2f}秒)\n")
                else:
                    log.write(f"失败\n")
        
        end_total_time = time.time()
        total_time = end_total_time - start_total_time
        
        result_message = f"SQL文件执行完成: 成功 {success_count}/{len(sql_files)}, 总耗时: {total_time:.2f}秒"
        print(f"\n{result_message}")
        
        # 记录总结果到日志
        with open(log_file, 'a', encoding='utf-8') as log:
            log.write(f"\n{result_message}\n")
        
        print(f"执行日志已保存到: {log_file}")
        
    except Exception as e:
        error_message = f"执行过程中发生错误: {str(e)}"
        print(error_message)
        
        # 记录错误到日志
        with open(log_file, 'a', encoding='utf-8') as log:
            log.write(f"\n{error_message}\n")
    finally:
        # 关闭数据库连接
        if 'conn' in locals() and conn is not None:
            conn.close()
            print("数据库连接已关闭")

def parse_arguments():
    """
    解析命令行参数
    """
    parser = argparse.ArgumentParser(description='批量执行SQL文件脚本')
    parser.add_argument('--dbname', default=DEFAULT_DB_PARAMS['dbname'], help='数据库名称')
    parser.add_argument('--user', default=DEFAULT_DB_PARAMS['user'], help='用户名')
    parser.add_argument('--password', default=DEFAULT_DB_PARAMS['password'], help='密码')
    parser.add_argument('--host', default=DEFAULT_DB_PARAMS['host'], help='主机地址')
    parser.add_argument('--port', default=DEFAULT_DB_PARAMS['port'], help='端口号')
    parser.add_argument('--retry', type=int, default=MAX_RETRY, help='最大重试次数')
    parser.add_argument('--dir', help='SQL文件目录，默认为脚本所在目录')
    
    return parser.parse_args()

def main():
    # 解析命令行参数
    args = parse_arguments()
    
    # 设置数据库连接参数
    db_params = {
        'dbname': args.dbname,
        'user': args.user,
        'password': args.password,
        'host': args.host,
        'port': args.port
    }
    
    # 获取SQL文件目录
    if args.dir:
        sql_dir = args.dir
    else:
        sql_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("="*80)
    print(f"开始执行SQL文件批处理")
    print(f"目录: {sql_dir}")
    print(f"数据库: {db_params['dbname']}@{db_params['host']}:{db_params['port']}")
    print(f"最大重试次数: {args.retry}")
    print("注意：脚本将尝试使用多种编码（utf-8, gbk, gb2312, gb18030, latin1）读取SQL文件")
    print("="*80)
    
    execute_sql_files_in_directory(sql_dir, db_params, args.retry)
    
    print("="*80)
    print("SQL文件批处理执行完成")
    print("="*80)

if __name__ == "__main__":
    main()