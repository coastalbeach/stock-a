#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
股票财务数据获取模块

获取A股股票的财务数据，包括资产负债表、利润表、现金流量表等
"""

import os
import sys
import pandas as pd
import numpy as np
import psycopg2
import psycopg2.extras
import yaml
from pathlib import Path
from datetime import datetime
import time

# 添加项目根目录到系统路径
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入AKShare
import akshare as ak


class StockFinancialData:
    """股票财务数据获取类"""
    
    def __init__(self):
        """初始化数据库连接"""
        self.conn = None
        self.cursor = None
        self.config = self._load_config()
        self.connect_db()
        
    def _load_config(self):
        """加载数据库配置"""
        config_path = os.path.join(project_root, 'config', 'connection.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 加载表结构配置
        tables_path = os.path.join(project_root, 'config', 'tables.yaml')
        with open(tables_path, 'r', encoding='utf-8') as f:
            tables_config = yaml.safe_load(f)
            
        # 合并配置
        config['tables'] = tables_config['tables']
        return config
    
    def connect_db(self):
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
            print("数据库连接成功")
        except Exception as e:
            print(f"数据库连接失败: {e}")
            sys.exit(1)
    
    def close_db(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("数据库连接已关闭")
    
    def get_stock_list(self):
        """从数据库获取股票列表
        
        Returns:
            list: 股票代码列表
        """
        try:
            # 从股票基本信息表获取股票列表
            query = """
            SELECT "股票代码", "股票名称", "市场" 
            FROM "股票基本信息"
            """
            self.cursor.execute(query)
            stocks = self.cursor.fetchall()
            
            # 转换为列表
            stock_list = []
            for stock in stocks:
                # 转换为AKShare接口需要的格式
                code = stock['股票代码']
                market = stock['市场']
                if market in ["沪A","科创"]:
                    symbol = f"SH{code}"
                elif market in ["深A", "创业"]:
                    symbol = f"SZ{code}"
                else:
                    symbol = f"BJ{code}"
                
                stock_list.append({
                    'symbol': symbol,
                    'code': code,
                    'name': stock['股票名称']
                })
            
            return stock_list
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return []
    
    def create_balance_sheet_table(self):
        """创建资产负债表"""
        try:
            # 创建表SQL
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS "资产负债表" (
                "股票代码" VARCHAR(10) NOT NULL,
                "报告期" DATE NOT NULL,
                "报表类型" VARCHAR(20) NOT NULL,
                "货币资金" FLOAT,
                "交易性金融资产" FLOAT,
                "应收票据" FLOAT,
                "应收账款" FLOAT,
                "应收款项融资" FLOAT,
                "预付款项" FLOAT,
                "其他应收款" FLOAT,
                "存货" FLOAT,
                "流动资产合计" FLOAT,
                "长期股权投资" FLOAT,
                "固定资产" FLOAT,
                "在建工程" FLOAT,
                "无形资产" FLOAT,
                "商誉" FLOAT,
                "非流动资产合计" FLOAT,
                "资产总计" FLOAT,
                "短期借款" FLOAT,
                "应付票据" FLOAT,
                "应付账款" FLOAT,
                "预收款项" FLOAT,
                "应付职工薪酬" FLOAT,
                "应交税费" FLOAT,
                "其他应付款" FLOAT,
                "流动负债合计" FLOAT,
                "长期借款" FLOAT,
                "应付债券" FLOAT,
                "非流动负债合计" FLOAT,
                "负债合计" FLOAT,
                "实收资本" FLOAT,
                "资本公积" FLOAT,
                "盈余公积" FLOAT,
                "未分配利润" FLOAT,
                "归属于母公司股东权益合计" FLOAT,
                "股东权益合计" FLOAT,
                "负债和股东权益总计" FLOAT,
                "更新时间" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY ("股票代码", "报告期", "报表类型")
            );
            """
            
            # 创建索引SQL
            create_index_sql = """
            CREATE INDEX IF NOT EXISTS idx_balance_股票代码 ON "资产负债表" ("股票代码");
            CREATE INDEX IF NOT EXISTS idx_balance_报告期 ON "资产负债表" ("报告期");
            """
            
            # 执行SQL
            self.cursor.execute(create_table_sql)
            self.cursor.execute(create_index_sql)
            self.conn.commit()
            print("资产负债表创建成功")
        except Exception as e:
            self.conn.rollback()
            print(f"创建资产负债表失败: {e}")
    
    def fetch_balance_sheet(self, symbol):
        """获取单个股票的资产负债表数据
        
        Args:
            symbol (str): 股票代码，格式为SH/SZ+代码，如SH600519
            
        Returns:
            pandas.DataFrame: 资产负债表数据
        """
        try:
            # 获取按报告期的资产负债表
            df = ak.stock_balance_sheet_by_report_em(symbol=symbol)
            
            if df.empty:
                print(f"未获取到 {symbol} 的资产负债表数据")
                return pd.DataFrame()
            
            # 提取股票代码（去掉市场标识）
            stock_code = symbol[2:]
            
            # 处理日期格式
            df['REPORT_DATE'] = pd.to_datetime(df['REPORT_DATE'])
            
            # 选择需要的列并重命名
            selected_columns = {
                'REPORT_DATE': '报告期',
                'REPORT_TYPE': '报表类型',
                'MONETARY_FUND': '货币资金',
                'TRADING_FINANCIAL_ASSETS': '交易性金融资产',
                'BILL_RECEIVABLE': '应收票据',
                'ACCOUNT_RECEIVABLE': '应收账款',
                'RECEIVABLE_FINANCING': '应收款项融资',
                'PREPAYMENT': '预付款项',
                'OTHER_RECEIVABLES': '其他应收款',
                'INVENTORY': '存货',
                'TOTAL_CURRENT_ASSETS': '流动资产合计',
                'LT_EQUITY_INVEST': '长期股权投资',
                'FIXED_ASSETS': '固定资产',
                'CIP': '在建工程',
                'INTANGIBLE_ASSETS': '无形资产',
                'GOODWILL': '商誉',
                'TOTAL_NONCURRENT_ASSETS': '非流动资产合计',
                'TOTAL_ASSETS': '资产总计',
                'ST_LOAN': '短期借款',
                'BILL_PAYABLE': '应付票据',
                'ACCOUNT_PAYABLE': '应付账款',
                'ADVANCE_RECEIVABLES': '预收款项',
                'PAYROLL_PAYABLE': '应付职工薪酬',
                'TAX_PAYABLE': '应交税费',
                'OTHER_PAYABLES': '其他应付款',
                'TOTAL_CURRENT_LIAB': '流动负债合计',
                'LT_LOAN': '长期借款',
                'BONDS_PAYABLE': '应付债券',
                'TOTAL_NONCURRENT_LIAB': '非流动负债合计',
                'TOTAL_LIABILITIES': '负债合计',
                'SHARE_CAPITAL': '实收资本',
                'CAPITAL_RESERVE': '资本公积',
                'SURPLUS_RESERVE': '盈余公积',
                'RETAINED_EARNING': '未分配利润',
                'TOTAL_EQUITY_PARENT': '归属于母公司股东权益合计',
                'TOTAL_EQUITY': '股东权益合计',
                'TOTAL_LIAB_EQUITY': '负债和股东权益总计'
            }
            
            # 筛选存在的列
            existing_columns = {k: v for k, v in selected_columns.items() if k in df.columns}
            
            # 重命名列
            result_df = df[list(existing_columns.keys())].rename(columns=existing_columns)
            
            # 添加股票代码列
            result_df['股票代码'] = stock_code
            
            # 将数值列转换为浮点数
            for col in result_df.columns:
                if col not in ['股票代码', '报告期', '报表类型']:
                    result_df[col] = pd.to_numeric(result_df[col], errors='coerce')
            
            # 调整列顺序
            cols = ['股票代码', '报告期', '报表类型'] + [col for col in result_df.columns if col not in ['股票代码', '报告期', '报表类型']]
            result_df = result_df[cols]
            
            return result_df
        except Exception as e:
            print(f"获取 {symbol} 资产负债表数据失败: {e}")
            return pd.DataFrame()
    
    def save_balance_sheet_to_db(self, df):
        """将资产负债表数据保存到数据库
        
        Args:
            df (pandas.DataFrame): 资产负债表数据
        """
        if df.empty:
            print("没有资产负债表数据需要保存")
            return
        
        try:
            # 先创建表
            self.create_balance_sheet_table()
            
            # 准备插入数据
            records = df.to_dict('records')
            
            # 获取列名
            columns = list(df.columns)
            
            # 构建UPSERT语句（插入或更新）
            insert_sql = f"""
            INSERT INTO "资产负债表" ("{'", "'.join(columns)}") 
            VALUES %s 
            ON CONFLICT ("股票代码", "报告期", "报表类型") DO UPDATE SET 
            {', '.join([f'"{col}" = EXCLUDED."{col}"' for col in columns if col not in ['股票代码', '报告期', '报表类型']])},
            "更新时间" = CURRENT_TIMESTAMP
            """
            
            # 准备数据
            values = [tuple(record.values()) for record in records]
            
            # 执行批量插入
            psycopg2.extras.execute_values(self.cursor, insert_sql, values)
            self.conn.commit()
            print(f"成功保存 {len(records)} 条资产负债表数据到数据库")
        except Exception as e:
            self.conn.rollback()
            print(f"保存资产负债表数据到数据库失败: {e}")
    
    def fetch_and_save_balance_sheet(self, limit=None):
        """获取并保存所有股票的资产负债表数据
        
        Args:
            limit (int, optional): 限制处理的股票数量，用于测试。默认为None，表示处理所有股票。
        """
        try:
            # 获取股票列表
            stock_list = self.get_stock_list()
            
            if limit:
                stock_list = stock_list[:limit]
            
            print(f"开始获取 {len(stock_list)} 只股票的资产负债表数据...")
            
            # 遍历股票列表，获取并保存资产负债表数据
            for i, stock in enumerate(stock_list):
                symbol = stock['symbol']
                name = stock['name']
                
                print(f"[{i+1}/{len(stock_list)}] 正在处理 {symbol} {name} 的资产负债表数据...")
                
                # 获取资产负债表数据
                balance_sheet_df = self.fetch_balance_sheet(symbol)
                
                if not balance_sheet_df.empty:
                    # 保存到数据库
                    self.save_balance_sheet_to_db(balance_sheet_df)
                    print(f"{symbol} {name} 资产负债表数据处理完成")
                else:
                    print(f"{symbol} {name} 没有资产负债表数据")
                
                # 避免频繁请求导致被封IP
                if i < len(stock_list) - 1:
                    import time
                    time.sleep(1)
            
            print("所有股票的资产负债表数据获取和保存完成")
        except Exception as e:
            print(f"获取和保存资产负债表数据过程中发生错误: {e}")
    
    def create_profit_sheet_table(self):
        """创建利润表"""
        try:
            # 创建表SQL
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS "利润表" (
                "股票代码" VARCHAR(10) NOT NULL,
                "报告期" DATE NOT NULL,
                "报表类型" VARCHAR(20) NOT NULL,
                "营业总收入" FLOAT,
                "营业收入" FLOAT,
                "营业总成本" FLOAT,
                "营业成本" FLOAT,
                "销售费用" FLOAT,
                "管理费用" FLOAT,
                "研发费用" FLOAT,
                "财务费用" FLOAT,
                "投资收益" FLOAT,
                "公允价值变动收益" FLOAT,
                "营业利润" FLOAT,
                "营业外收入" FLOAT,
                "营业外支出" FLOAT,
                "利润总额" FLOAT,
                "所得税费用" FLOAT,
                "净利润" FLOAT,
                "归属于母公司股东的净利润" FLOAT,
                "少数股东损益" FLOAT,
                "基本每股收益" FLOAT,
                "稀释每股收益" FLOAT,
                "更新时间" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY ("股票代码", "报告期", "报表类型")
            );
            """
            
            # 创建索引SQL
            create_index_sql = """
            CREATE INDEX IF NOT EXISTS idx_profit_股票代码 ON "利润表" ("股票代码");
            CREATE INDEX IF NOT EXISTS idx_profit_报告期 ON "利润表" ("报告期");
            """
            
            # 执行SQL
            self.cursor.execute(create_table_sql)
            self.cursor.execute(create_index_sql)
            self.conn.commit()
            print("利润表创建成功")
        except Exception as e:
            self.conn.rollback()
            print(f"创建利润表失败: {e}")
    
    def create_cash_flow_table(self):
        """创建现金流量表"""
        try:
            # 创建表SQL
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS "现金流量表" (
                "股票代码" VARCHAR(10) NOT NULL,
                "报告期" DATE NOT NULL,
                "报表类型" VARCHAR(20) NOT NULL,
                "经营活动产生的现金流量净额" FLOAT,
                "销售商品、提供劳务收到的现金" FLOAT,
                "收到的税费返还" FLOAT,
                "收到其他与经营活动有关的现金" FLOAT,
                "经营活动现金流入小计" FLOAT,
                "购买商品、接受劳务支付的现金" FLOAT,
                "支付给职工以及为职工支付的现金" FLOAT,
                "支付的各项税费" FLOAT,
                "支付其他与经营活动有关的现金" FLOAT,
                "经营活动现金流出小计" FLOAT,
                "投资活动产生的现金流量净额" FLOAT,
                "收回投资收到的现金" FLOAT,
                "取得投资收益收到的现金" FLOAT,
                "处置固定资产、无形资产和其他长期资产收回的现金净额" FLOAT,
                "投资活动现金流入小计" FLOAT,
                "购建固定资产、无形资产和其他长期资产支付的现金" FLOAT,
                "投资支付的现金" FLOAT,
                "投资活动现金流出小计" FLOAT,
                "筹资活动产生的现金流量净额" FLOAT,
                "吸收投资收到的现金" FLOAT,
                "取得借款收到的现金" FLOAT,
                "筹资活动现金流入小计" FLOAT,
                "偿还债务支付的现金" FLOAT,
                "分配股利、利润或偿付利息支付的现金" FLOAT,
                "筹资活动现金流出小计" FLOAT,
                "现金及现金等价物净增加额" FLOAT,
                "期初现金及现金等价物余额" FLOAT,
                "期末现金及现金等价物余额" FLOAT,
                "更新时间" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY ("股票代码", "报告期", "报表类型")
            );
            """
            
            # 创建索引SQL
            create_index_sql = """
            CREATE INDEX IF NOT EXISTS idx_cash_flow_股票代码 ON "现金流量表" ("股票代码");
            CREATE INDEX IF NOT EXISTS idx_cash_flow_报告期 ON "现金流量表" ("报告期");
            """
            
            # 执行SQL
            self.cursor.execute(create_table_sql)
            self.cursor.execute(create_index_sql)
            self.conn.commit()
            print("现金流量表创建成功")
        except Exception as e:
            self.conn.rollback()
            print(f"创建现金流量表失败: {e}")
    
    def fetch_profit_sheet(self, symbol):
        """获取单个股票的利润表数据
        
        Args:
            symbol (str): 股票代码，格式为SH/SZ/BJ+代码
            
        Returns:
            pandas.DataFrame: 利润表数据
        """
        try:
            # 获取按报告期的利润表
            df = ak.stock_profit_sheet_by_report_em(symbol=symbol)
            
            if df.empty:
                print(f"未获取到 {symbol} 的利润表数据")
                return pd.DataFrame()
            
            # 提取股票代码（去掉市场标识）
            stock_code = symbol[2:]
            
            # 处理日期格式
            df['REPORT_DATE'] = pd.to_datetime(df['REPORT_DATE'])
            
            # 选择需要的列并重命名
            selected_columns = {
                'REPORT_DATE': '报告期',
                'REPORT_TYPE': '报表类型',
                'TOTAL_OPERATE_INCOME': '营业总收入',
                'OPERATE_INCOME': '营业收入',
                'TOTAL_OPERATE_COST': '营业总成本',
                'OPERATE_COST': '营业成本',
                'SALE_EXPENSE': '销售费用',
                'MANAGE_EXPENSE': '管理费用',
                'RESEARCH_EXPENSE': '研发费用',
                'FINANCE_EXPENSE': '财务费用',
                'INVEST_INCOME': '投资收益',
                'FAIR_VALUE_CHANGE_INCOME': '公允价值变动收益',
                'OPERATE_PROFIT': '营业利润',
                'NONBUSINESS_INCOME': '营业外收入',
                'NONBUSINESS_EXPENSE': '营业外支出',
                'TOTAL_PROFIT': '利润总额',
                'INCOME_TAX': '所得税费用',
                'NETPROFIT': '净利润',
                'PARENT_NETPROFIT': '归属于母公司股东的净利润',
                'MINORITY_INTEREST': '少数股东损益',
                'BASIC_EPS': '基本每股收益',
                'DILUTED_EPS': '稀释每股收益'
            }
            
            # 筛选存在的列
            existing_columns = {k: v for k, v in selected_columns.items() if k in df.columns}
            
            # 重命名列
            result_df = df[list(existing_columns.keys())].rename(columns=existing_columns)
            
            # 添加股票代码列
            result_df['股票代码'] = stock_code
            
            # 将数值列转换为浮点数
            for col in result_df.columns:
                if col not in ['股票代码', '报告期', '报表类型']:
                    result_df[col] = pd.to_numeric(result_df[col], errors='coerce')
            
            # 调整列顺序
            cols = ['股票代码', '报告期', '报表类型'] + [col for col in result_df.columns if col not in ['股票代码', '报告期', '报表类型']]
            result_df = result_df[cols]
            
            return result_df
        except Exception as e:
            print(f"获取 {symbol} 利润表数据失败: {e}")
            return pd.DataFrame()
    
    def fetch_cash_flow(self, symbol):
        """获取单个股票的现金流量表数据
        
        Args:
            symbol (str): 股票代码，格式为SH/SZ+代码，如SH600519
            
        Returns:
            pandas.DataFrame: 现金流量表数据
        """
        try:
            # 获取按报告期的现金流量表
            df = ak.stock_cash_flow_sheet_by_report_em(symbol=symbol)
            
            if df.empty:
                print(f"未获取到 {symbol} 的现金流量表数据")
                return pd.DataFrame()
            
            # 提取股票代码（去掉市场标识）
            stock_code = symbol[2:]
            
            # 处理日期格式
            df['REPORT_DATE'] = pd.to_datetime(df['REPORT_DATE'])
            
            # 选择需要的列并重命名
            selected_columns = {
                'REPORT_DATE': '报告期',
                'REPORT_TYPE': '报表类型',
                'NETCASH_OPERATE': '经营活动产生的现金流量净额',
                'SALES_SERVICES': '销售商品、提供劳务收到的现金',
                'TAX_REFUND': '收到的税费返还',
                'OTHER_OPERATE_CASH': '收到其他与经营活动有关的现金',
                'OPERATE_CASH_TOTAL': '经营活动现金流入小计',
                'BUY_SERVICES': '购买商品、接受劳务支付的现金',
                'EMPLOYEE_CASH': '支付给职工以及为职工支付的现金',
                'TAX_CASH': '支付的各项税费',
                'OTHER_OPERATE_CASH_PAID': '支付其他与经营活动有关的现金',
                'OPERATE_CASH_PAID_TOTAL': '经营活动现金流出小计',
                'NETCASH_INVEST': '投资活动产生的现金流量净额',
                'INVEST_RECOVERY': '收回投资收到的现金',
                'INVEST_INCOME': '取得投资收益收到的现金',
                'DISPOSAL_ASSETS': '处置固定资产、无形资产和其他长期资产收回的现金净额',
                'INVEST_CASH_TOTAL': '投资活动现金流入小计',
                'CONSTRUCT_LONG_ASSET': '购建固定资产、无形资产和其他长期资产支付的现金',
                'INVEST_PAID': '投资支付的现金',
                'INVEST_CASH_PAID_TOTAL': '投资活动现金流出小计',
                'NETCASH_FINANCE': '筹资活动产生的现金流量净额',
                'ACCEPT_INVEST': '吸收投资收到的现金',
                'LOAN': '取得借款收到的现金',
                'FINANCE_CASH_TOTAL': '筹资活动现金流入小计',
                'REPAY_DEBT': '偿还债务支付的现金',
                'INTEREST_DIVIDEND': '分配股利、利润或偿付利息支付的现金',
                'FINANCE_CASH_PAID_TOTAL': '筹资活动现金流出小计',
                'CASH_EQUIVALENT_INCREASE': '现金及现金等价物净增加额',
                'BEGIN_CASH': '期初现金及现金等价物余额',
                'END_CASH': '期末现金及现金等价物余额'
            }
            
            # 筛选存在的列
            existing_columns = {k: v for k, v in selected_columns.items() if k in df.columns}
            
            # 重命名列
            result_df = df[list(existing_columns.keys())].rename(columns=existing_columns)
            
            # 添加股票代码列
            result_df['股票代码'] = stock_code
            
            # 将数值列转换为浮点数
            for col in result_df.columns:
                if col not in ['股票代码', '报告期', '报表类型']:
                    result_df[col] = pd.to_numeric(result_df[col], errors='coerce')
            
            # 调整列顺序
            cols = ['股票代码', '报告期', '报表类型'] + [col for col in result_df.columns if col not in ['股票代码', '报告期', '报表类型']]
            result_df = result_df[cols]
            
            return result_df
        except Exception as e:
            print(f"获取 {symbol} 现金流量表数据失败: {e}")
            return pd.DataFrame()
    
    def save_profit_sheet_to_db(self, df):
        """将利润表数据保存到数据库
        
        Args:
            df (pandas.DataFrame): 利润表数据
        """
        if df.empty:
            print("没有利润表数据需要保存")
            return
        
        try:
            # 先创建表
            self.create_profit_sheet_table()
            
            # 准备插入数据
            records = df.to_dict('records')
            
            # 获取列名
            columns = list(df.columns)
            
            # 构建UPSERT语句（插入或更新）
            insert_sql = f"""
            INSERT INTO "利润表" ("{'", "'.join(columns)}") 
            VALUES %s 
            ON CONFLICT ("股票代码", "报告期", "报表类型") DO UPDATE SET 
            {', '.join([f'"{col}" = EXCLUDED."{col}"' for col in columns if col not in ['股票代码', '报告期', '报表类型']])},
            "更新时间" = CURRENT_TIMESTAMP
            """
            
            # 准备数据
            values = [tuple(record.values()) for record in records]
            
            # 执行批量插入
            psycopg2.extras.execute_values(self.cursor, insert_sql, values)
            self.conn.commit()
            print(f"成功保存 {len(records)} 条利润表数据到数据库")
        except Exception as e:
            self.conn.rollback()
            print(f"保存利润表数据到数据库失败: {e}")
    
    def save_cash_flow_to_db(self, df):
        """将现金流量表数据保存到数据库
        
        Args:
            df (pandas.DataFrame): 现金流量表数据
        """
        if df.empty:
            print("没有现金流量表数据需要保存")
            return
        
        try:
            # 先创建表
            self.create_cash_flow_table()
            
            # 准备插入数据
            records = df.to_dict('records')
            
            # 获取列名
            columns = list(df.columns)
            
            # 构建UPSERT语句（插入或更新）
            insert_sql = f"""
            INSERT INTO "现金流量表" ("{'", "'.join(columns)}") 
            VALUES %s 
            ON CONFLICT ("股票代码", "报告期", "报表类型") DO UPDATE SET 
            {', '.join([f'"{col}" = EXCLUDED."{col}"' for col in columns if col not in ['股票代码', '报告期', '报表类型']])},
            "更新时间" = CURRENT_TIMESTAMP
            """
            
            # 准备数据
            values = [tuple(record.values()) for record in records]
            
            # 执行批量插入
            psycopg2.extras.execute_values(self.cursor, insert_sql, values)
            self.conn.commit()
            print(f"成功保存 {len(records)} 条现金流量表数据到数据库")
        except Exception as e:
            self.conn.rollback()
            print(f"保存现金流量表数据到数据库失败: {e}")
    
    def fetch_and_save_profit_sheet(self, limit=None):
        """获取并保存所有股票的利润表数据
        
        Args:
            limit (int, optional): 限制处理的股票数量，用于测试。默认为None，表示处理所有股票。
        """
        try:
            # 获取股票列表
            stock_list = self.get_stock_list()
            
            if limit:
                stock_list = stock_list[:limit]
            
            print(f"开始获取 {len(stock_list)} 只股票的利润表数据...")
            
            # 遍历股票列表，获取并保存利润表数据
            for i, stock in enumerate(stock_list):
                symbol = stock['symbol']
                name = stock['name']
                
                print(f"[{i+1}/{len(stock_list)}] 正在处理 {symbol} {name} 的利润表数据...")
                
                # 获取利润表数据
                profit_sheet_df = self.fetch_profit_sheet(symbol)
                
                if not profit_sheet_df.empty:
                    # 保存到数据库
                    self.save_profit_sheet_to_db(profit_sheet_df)
                    print(f"{symbol} {name} 利润表数据处理完成")
                else:
                    print(f"{symbol} {name} 没有利润表数据")
                
                # 避免频繁请求导致被封IP
                if i < len(stock_list) - 1:
                    time.sleep(1)
            
            print("所有股票的利润表数据获取和保存完成")
        except Exception as e:
            print(f"获取和保存利润表数据过程中发生错误: {e}")
    
    def fetch_and_save_cash_flow(self, limit=None):
        """获取并保存所有股票的现金流量表数据
        
        Args:
            limit (int, optional): 限制处理的股票数量，用于测试。默认为None，表示处理所有股票。
        """
        try:
            # 获取股票列表
            stock_list = self.get_stock_list()
            
            if limit:
                stock_list = stock_list[:limit]
            
            print(f"开始获取 {len(stock_list)} 只股票的现金流量表数据...")
            
            # 遍历股票列表，获取并保存现金流量表数据
            for i, stock in enumerate(stock_list):
                symbol = stock['symbol']
                name = stock['name']
                
                print(f"[{i+1}/{len(stock_list)}] 正在处理 {symbol} {name} 的现金流量表数据...")
                
                # 获取现金流量表数据
                cash_flow_df = self.fetch_cash_flow(symbol)
                
                if not cash_flow_df.empty:
                    # 保存到数据库
                    self.save_cash_flow_to_db(cash_flow_df)
                    print(f"{symbol} {name} 现金流量表数据处理完成")
                else:
                    print(f"{symbol} {name} 没有现金流量表数据")
                
                # 避免频繁请求导致被封IP
                if i < len(stock_list) - 1:
                    time.sleep(1)
            
            print("所有股票的现金流量表数据获取和保存完成")
        except Exception as e:
            print(f"获取和保存现金流量表数据过程中发生错误: {e}")
    
    def run(self, limit=None):
        """运行财务数据获取和保存流程
        
        Args:
            limit (int, optional): 限制处理的股票数量，用于测试。默认为None，表示处理所有股票。
        """
        try:
            print("开始获取股票财务数据...")
            # 获取并保存资产负债表数据
            self.fetch_and_save_balance_sheet(limit)
            # 获取并保存利润表数据
            self.fetch_and_save_profit_sheet(limit)
            # 获取并保存现金流量表数据
            self.fetch_and_save_cash_flow(limit)
            print("股票财务数据获取和保存完成")
        except Exception as e:
            print(f"运行过程中发生错误: {e}")
        finally:
            # 关闭数据库连接
            self.close_db()


if __name__ == "__main__":
    # 创建实例并运行，可以设置limit参数限制处理的股票数量，用于测试
    stock_financial_data = StockFinancialData()
    stock_financial_data.run(limit=5)  # 测试时只处理5只股票