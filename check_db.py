#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库检查脚本

用于检查PostgreSQL数据库连接和数据表内容
"""

import psycopg2
import pandas as pd

def check_database():
    """检查数据库连接和表内容"""
    try:
        # 连接到PostgreSQL数据库
        print("尝试连接数据库...")
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="stocka",
            user="postgres",
            password="111222"
        )
        print("数据库连接成功!")
        
        # 创建游标
        cursor = conn.cursor()
        
        # 检查各种可能的股票历史行情表名
        possible_tables = ['日线行情', '股票历史行情_后复权', '股票历史行情_前复权', '股票历史行情_不复权']
        
        for table_name in possible_tables:
            cursor.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table_name}'
                )
            """)
            table_exists = cursor.fetchone()[0]
            print(f"'{table_name}'表是否存在: {table_exists}")
            
            if table_exists:
                # 检查表中的记录数
                cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                count = cursor.fetchone()[0]
                print(f"'{table_name}'表中的记录数: {count}")
                
                # 检查是否有股票代码为000001的数据
                cursor.execute(f'SELECT COUNT(*) FROM "{table_name}" WHERE "股票代码" = \'000001\'')
                count_000001 = cursor.fetchone()[0]
                print(f"'{table_name}'表中股票代码为000001的记录数: {count_000001}")
                
                if count_000001 > 0:
                    # 获取最近的几条记录
                    cursor.execute(f'SELECT "股票代码", "日期", "收盘" FROM "{table_name}" WHERE "股票代码" = \'000001\' ORDER BY "日期" DESC LIMIT 5')
                    recent_records = cursor.fetchall()
                    print(f"\n'{table_name}'表中最近的几条记录:")
                    for record in recent_records:
                        print(f"  {record[0]} - {record[1]} - {record[2]}")
                
                # 检查表结构
                cursor.execute(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}'
                    LIMIT 10
                """)
                columns = cursor.fetchall()
                print(f"\n'{table_name}'表结构(前10列):")
                for col in columns:
                    print(f"  {col[0]} - {col[1]}")
                print("\n")
                
        # 特别检查'股票历史行情_不复权'表中的数据
        if '股票历史行情_不复权' in possible_tables:
            print("\n特别检查'股票历史行情_不复权'表中的数据:")
            # 检查表中的日期范围
            cursor.execute('SELECT MIN("日期"), MAX("日期") FROM "股票历史行情_不复权"')
            date_range = cursor.fetchone()
            print(f"日期范围: {date_range[0]} 至 {date_range[1]}")
            
            # 检查股票代码列表
            cursor.execute('SELECT DISTINCT "股票代码" FROM "股票历史行情_不复权" LIMIT 10')
            stock_codes = cursor.fetchall()
            print("股票代码列表(前10个):")
            for code in stock_codes:
                print(f"  {code[0]}")
            
            # 检查000001的数据
            cursor.execute('SELECT COUNT(*) FROM "股票历史行情_不复权" WHERE "股票代码" = \'000001\'')
            count_000001 = cursor.fetchone()[0]
            print(f"股票代码为000001的记录数: {count_000001}")
            
            if count_000001 > 0:
                # 获取日期范围
                cursor.execute('SELECT MIN("日期"), MAX("日期") FROM "股票历史行情_不复权" WHERE "股票代码" = \'000001\'')
                date_range_000001 = cursor.fetchone()
                print(f"000001的日期范围: {date_range_000001[0]} 至 {date_range_000001[1]}")
                
                # 获取最近的几条记录
                cursor.execute('SELECT "股票代码", "日期", "开盘", "收盘", "最高", "最低" FROM "股票历史行情_不复权" WHERE "股票代码" = \'000001\' ORDER BY "日期" DESC LIMIT 5')
                recent_records = cursor.fetchall()
                print("\n000001最近的几条记录:")
                for record in recent_records:
                    print(f"  {record[0]} - {record[1]} - 开盘:{record[2]} 收盘:{record[3]} 最高:{record[4]} 最低:{record[5]}")
            else:
                print("股票代码000001在'股票历史行情_不复权'表中没有数据")
                
                # 检查是否有其他股票代码的数据
                cursor.execute('SELECT "股票代码", COUNT(*) FROM "股票历史行情_不复权" GROUP BY "股票代码" LIMIT 5')
                other_stocks = cursor.fetchall()
                if other_stocks:
                    print("\n其他股票代码的数据统计(前5个):")
                    for stock in other_stocks:
                        print(f"  {stock[0]} - {stock[1]}条记录")
                else:
                    print("'股票历史行情_不复权'表中没有任何数据")
        
        # 检查股票技术指标表
        cursor.execute("""SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = '股票技术指标'
        )""")
        tech_table_exists = cursor.fetchone()[0]
        print(f"\n'股票技术指标'表是否存在: {tech_table_exists}")
        
        if tech_table_exists:
            cursor.execute('SELECT COUNT(*) FROM "股票技术指标"')
            tech_count = cursor.fetchone()[0]
            print(f"'股票技术指标'表中的记录数: {tech_count}")
            
            # 检查是否有股票代码为000001的技术指标数据
            cursor.execute('SELECT COUNT(*) FROM "股票技术指标" WHERE "股票代码" = \'000001\'')
            tech_count_000001 = cursor.fetchone()[0]
            print(f"股票代码为000001的技术指标记录数: {tech_count_000001}")
        
        # 关闭连接
        cursor.close()
        conn.close()
        print("\n数据库连接已关闭")
        
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    check_database()