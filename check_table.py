# -*- coding: utf-8 -*-

import sys
import os
from pathlib import Path

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from db.postgresql_manager import PostgreSQLManager

def check_tables():
    """检查数据库中是否存在行业技术指标表"""
    try:
        # 连接数据库
        db = PostgreSQLManager()
        cursor = db.cursor
        
        # 查询行业技术指标表是否存在
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '行业技术指标'")
        industry_indicator_table = cursor.fetchone()
        print('行业技术指标表是否存在:', industry_indicator_table is not None)
        
        # 查询行业历史行情表是否存在
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '行业历史行情'")
        industry_history_table = cursor.fetchone()
        print('行业历史行情表是否存在:', industry_history_table is not None)
        
        # 如果行业历史行情表存在，检查是否有数据
        if industry_history_table is not None:
            cursor.execute("SELECT COUNT(*) FROM \"行业历史行情\" WHERE \"行业名称\" IN ('银行', '证券')")
            count = cursor.fetchone()[0]
            print(f'行业历史行情表中银行和证券行业的数据条数: {count}')
        
        # 关闭连接
        db.close()
        
    except Exception as e:
        print(f"检查表时出错: {e}")

if __name__ == "__main__":
    check_tables()