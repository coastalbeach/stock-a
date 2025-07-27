#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
股票历史行情数据获取模块

获取A股股票的历史行情数据，包括不复权和后复权数据
从2005年1月4日开始获取数据，存入数据库表"股票历史行情_不复权"和"股票历史行情_后复权"
"""

import os
import sys
import time
import datetime
import pandas as pd
import numpy as np
import psycopg2
import psycopg2.extras
import yaml
from pathlib import Path
from tqdm import tqdm
import concurrent.futures
import logging
import threading
from queue import Queue

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent.parent) 
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入工具模块
from utils.logger import LoggerManager
from utils.config_loader import load_connection_config, load_tables_config
from db import PostgreSQLManager

# 导入AKShare
import akshare as ak


#- 移除DatabasePool类，使用PostgreSQLManager的连接池功能


class StockHistoricalData:
    """股票历史行情数据获取类"""
    
    def __init__(self):
        """初始化"""
        # 初始化日志
        self.logger = self._init_logger()
        self.logger.info("初始化股票历史行情数据获取模块")
        
        # 加载配置
        self.connection_config = load_connection_config()
        self.tables_config = load_tables_config()
        
        # 初始化数据库连接池
        self.db = PostgreSQLManager(use_pool=True, max_connections=10)  # 使用连接池模式，增加连接数以支持更多线程
        
        # 设置基础参数
        self.start_date = "20050104"  # 起始日期：2005年1月4日
        self.today = datetime.datetime.now().strftime("%Y%m%d")
        self.is_trading_day = False
        self.is_trading_time = False
        self.last_trading_day = None
        self.previous_trading_day = None  # 前一个交易日
        self.last_run_time = None  # 上次运行时间
        self.last_run_in_trading_time = False  # 上次是否在交易时间运行
        
        # 配置网络请求参数
        self._setup_network_config()
        
        # 检查是否为交易日和交易时间
        self._check_trading_status()
        
        # 获取上次运行信息
        self._get_last_run_info()
    
    def _setup_network_config(self):
        """配置网络请求参数"""
        try:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            # 创建重试策略
            retry_strategy = Retry(
                total=3,
                status_forcelist=[429, 500, 502, 503, 504],
                method_whitelist=["HEAD", "GET", "OPTIONS"],
                backoff_factor=1
            )
            
            # 创建适配器
            adapter = HTTPAdapter(max_retries=retry_strategy)
            
            # 创建会话
            self.session = requests.Session()
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
            
            # 设置超时时间
            self.session.timeout = 30
            
            # 设置请求头，模拟浏览器
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
            
            self.logger.info("网络请求配置完成")
        except Exception as e:
            self.logger.warning(f"配置网络请求参数失败: {e}，将使用默认配置")
            self.session = None
        
    def _init_logger(self):
        """初始化日志记录器
        
        Returns:
            logging.Logger: 日志记录器
        """
        logger_manager = LoggerManager()
        logger = logger_manager.get_logger("stock_historical")
        return logger
    
    def _check_trading_status(self):
        """检查当前是否为交易日和交易时间
        
        优化策略：
        1. 首先尝试从Redis获取交易日信息
        2. 如果Redis没有数据，则从数据库获取最新交易日期作为查询起始日期
        3. 如果数据库也没有数据，则使用近7天作为查询范围
        4. 将最后两个交易日信息存入Redis并设置合理的过期时间
        5. 即使API调用失败，也使用工作日作为交易日确保程序继续运行
        """
        try:
            # 初始化Redis管理器
            from db import RedisManager
            redis_manager = RedisManager()
            
            # 尝试从Redis获取交易日信息
            redis_key = "stock:trading_days:latest"
            trading_days_info = redis_manager.get_value(redis_key)
            
            if trading_days_info:
                # 从Redis获取到交易日信息
                self.logger.info("从Redis获取交易日信息")
                trading_days_dict = trading_days_info
                self.last_trading_day = pd.to_datetime(trading_days_dict.get('last_trading_day'))
                self.previous_trading_day = pd.to_datetime(trading_days_dict.get('previous_trading_day'))
                self.logger.info(f"最后一个交易日: {self.last_trading_day}, 前一个交易日: {self.previous_trading_day}")
            else:
                # Redis中没有数据，需要重新获取
                self.logger.info("Redis中没有交易日信息，从数据库或API获取")
                
                # 从数据库获取最新交易日期作为查询起始日期
                start_date = self._get_latest_date_from_db()
                
                # 如果数据库中没有数据，使用近7天作为查询范围
                if not start_date:
                    start_date = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y%m%d")
                    self.logger.info(f"数据库中没有历史数据，使用近7天作为查询范围: {start_date}")
                else:
                    self.logger.info(f"从数据库获取到最新日期: {start_date}")
                
                # 尝试获取指数数据
                try:
                    import requests
                    from requests.exceptions import ConnectionError, Timeout, RequestException
                    import random
                    
                    # 定义重试参数
                    max_retries = 3
                    base_delay = 2
                    max_delay = 30
                    
                    index_data = None
                    for retry in range(max_retries):
                        try:
                            if retry > 0:
                                delay = min(base_delay * (2 ** retry) + random.uniform(0, 1), max_delay)
                                self.logger.info(f"获取上证指数第{retry+1}次重试，延时{delay:.2f}秒")
                                time.sleep(delay)
                            
                            self.logger.info(f"获取上证指数，起始日期: {start_date}, 结束日期: {self.today}")
                            index_data = ak.index_zh_a_hist(symbol="000001", period="daily", 
                                                          start_date=start_date, 
                                                          end_date=self.today)
                            if index_data is not None and not index_data.empty:
                                break
                        except (ConnectionError, Timeout, RequestException) as e:
                            if "Connection aborted" in str(e) or "Remote end closed connection" in str(e):
                                self.logger.warning(f"获取上证指数遇到连接问题: {e}，第{retry+1}/{max_retries}次重试")
                                if retry == max_retries - 1:
                                    self.logger.error(f"获取上证指数重试{max_retries}次后仍然失败")
                                continue
                            else:
                                self.logger.warning(f"获取上证指数遇到网络错误: {e}，第{retry+1}/{max_retries}次重试")
                                if retry == max_retries - 1:
                                    self.logger.error(f"获取上证指数重试{max_retries}次后仍然失败")
                                continue
                        except Exception as e:
                            self.logger.warning(f"获取上证指数异常: {e}")
                            if retry == max_retries - 1:
                                break
                            continue
                    
                    if not index_data.empty:
                        # 获取最后一个交易日
                        self.last_trading_day = index_data.iloc[-1]['日期']
                        
                        # 处理不同数据长度的情况
                        if len(index_data) >= 2:
                            # 有两个或更多交易日数据
                            self.previous_trading_day = index_data.iloc[-2]['日期']
                            self.logger.info(f"获取到最后一个交易日: {self.last_trading_day}, 前一个交易日: {self.previous_trading_day}")
                        elif len(index_data) == 1:
                            # 只有一个交易日数据
                            self.logger.info(f"获取到最后一个交易日: {self.last_trading_day}, 但没有前一个交易日数据")
                            # 尝试通过计算获取前一个工作日
                            last_date = pd.to_datetime(self.last_trading_day)
                            # 从最后交易日往前推一天
                            prev_date = last_date - datetime.timedelta(days=1)
                            # 如果是周末，继续往前推到周五
                            if prev_date.weekday() >= 5:  # 5是周六，6是周日
                                days_to_friday = prev_date.weekday() - 4
                                prev_date = prev_date - datetime.timedelta(days=days_to_friday)
                            self.previous_trading_day = prev_date
                            self.logger.info(f"计算得到可能的前一个交易日: {self.previous_trading_day}")
                        
                        # 将交易日信息存入Redis
                        trading_days_dict = {
                            'last_trading_day': self.last_trading_day.strftime("%Y-%m-%d") if isinstance(self.last_trading_day, pd.Timestamp) else str(self.last_trading_day),
                            'previous_trading_day': self.previous_trading_day.strftime("%Y-%m-%d") if isinstance(self.previous_trading_day, pd.Timestamp) else str(self.previous_trading_day)
                        }
                        
                        # 设置Redis过期时间：如果是交易日，则在当天9:30过期；否则在下一个工作日9:30过期
                        now = datetime.datetime.now()
                        today_930 = datetime.datetime.combine(now.date(), datetime.time(9, 30))
                        
                        # 如果当前时间已经过了9:30，则设置为明天9:30过期
                        if now.time() >= datetime.time(9, 30):
                            expire_time = today_930 + datetime.timedelta(days=1)
                        else:
                            expire_time = today_930
                        
                        # 计算过期秒数
                        expire_seconds = int((expire_time - now).total_seconds())
                        self.logger.info(f"将交易日信息存入Redis，过期时间: {expire_time}, {expire_seconds}秒后")
                        redis_manager.set_value(redis_key, trading_days_dict, expire=expire_seconds)
                    else:
                        self.logger.warning("获取上证指数数据为空")
                        self._set_default_trading_days()
                except Exception as e:
                    self.logger.warning(f"获取上证指数数据异常: {e}，使用默认工作日")
                    self._set_default_trading_days()
            
            # 关闭Redis连接
            redis_manager.close()
            
            # 判断今天是否为交易日
            self._check_if_today_is_trading_day()
            
        except Exception as e:
            self.logger.error(f"检查交易状态失败: {e}")
            # 即使出错，也设置默认交易日确保程序能继续运行
            self._set_default_trading_days()
            self._check_if_today_is_trading_day()
    
    def _get_latest_date_from_db(self):
        """从数据库获取最新交易日期
        
        Returns:
            str: 最新交易日期，格式为YYYYMMDD，如果没有数据则返回None
        """
        try:
            sql = "SELECT MAX(\"日期\") as last_date FROM \"股票历史行情_不复权\""
            result = self.db.query(sql)
            
            if result and result[0]['last_date']:
                last_date = result[0]['last_date']
                # 返回日期字符串，格式为YYYYMMDD
                return last_date.strftime("%Y%m%d")
            return None
        except Exception as e:
            self.logger.error(f"从数据库获取最新交易日期失败: {e}")
            return None
    
    def _set_default_trading_days(self):
        """设置默认交易日，确保程序能继续运行"""
        now = datetime.datetime.now()
        # 如果是周末，设置为上周五
        if now.weekday() >= 5:  # 5是周六，6是周日
            days_to_subtract = now.weekday() - 4  # 减去相应天数得到周五
            self.last_trading_day = (now - datetime.timedelta(days=days_to_subtract)).date()
            self.previous_trading_day = (now - datetime.timedelta(days=days_to_subtract+1)).date()
        else:
            # 工作日
            self.last_trading_day = now.date()
            self.previous_trading_day = (now - datetime.timedelta(days=1)).date()
            # 如果前一天是周末，则设置为上周五
            if self.previous_trading_day.weekday() >= 5:
                days_to_friday = self.previous_trading_day.weekday() - 4
                self.previous_trading_day = (self.previous_trading_day - datetime.timedelta(days=days_to_friday)).date()
        
        self.logger.warning(f"使用默认交易日: 最后交易日={self.last_trading_day}, 前一交易日={self.previous_trading_day}")
    
    def _check_if_today_is_trading_day(self):
        """判断今天是否为交易日和交易时间"""
        today_date = datetime.datetime.now().date()
        
        # 将last_trading_day转换为日期对象进行比较
        if isinstance(self.last_trading_day, str):
            last_trading_day_date = pd.to_datetime(self.last_trading_day).date()
        elif isinstance(self.last_trading_day, pd.Timestamp):
            last_trading_day_date = self.last_trading_day.date()
        else:
            last_trading_day_date = self.last_trading_day
            
        if last_trading_day_date == today_date:
            self.is_trading_day = True
            self.logger.info("今天是交易日")
            
            # 判断当前是否为交易时间 (9:30-11:30, 13:00-15:00)
            now = datetime.datetime.now().time()
            morning_start = datetime.time(9, 30)
            morning_end = datetime.time(11, 30)
            afternoon_start = datetime.time(13, 0)
            afternoon_end = datetime.time(15, 0)
            
            if (morning_start <= now <= morning_end) or (afternoon_start <= now <= afternoon_end):
                self.is_trading_time = True
                self.logger.info("当前是交易时间")
            else:
                self.logger.info("当前不是交易时间")
        else:
            self.logger.info("今天不是交易日")
            
    def _get_last_run_info(self):
        """获取上次运行信息
        
        从Redis中获取上次运行时间和是否在交易时间运行的信息
        """
        try:
            # 初始化Redis管理器
            from db import RedisManager
            redis_manager = RedisManager()
            
            # 尝试从Redis获取上次运行信息
            redis_key = "stock:historical:last_run_info"
            last_run_info = redis_manager.get_value(redis_key)
            
            if last_run_info:
                self.last_run_time = pd.to_datetime(last_run_info.get('last_run_time'))
                self.last_run_in_trading_time = last_run_info.get('in_trading_time', False)
                self.logger.info(f"上次运行时间: {self.last_run_time}, 是否在交易时间: {self.last_run_in_trading_time}")
            else:
                self.logger.info("没有找到上次运行信息记录")
                
            # 关闭Redis连接
            redis_manager.close()
        except Exception as e:
            self.logger.error(f"获取上次运行信息失败: {e}")
            
    def _save_run_info(self):
        """保存本次运行信息
        
        将当前运行时间和是否在交易时间运行的信息保存到Redis
        """
        try:
            # 初始化Redis管理器
            from db import RedisManager
            redis_manager = RedisManager()
            
            # 准备运行信息
            now = datetime.datetime.now()
            run_info = {
                'last_run_time': now.strftime("%Y-%m-%d %H:%M:%S"),
                'in_trading_time': self.is_trading_time
            }
            
            # 保存到Redis
            redis_key = "stock:historical:last_run_info"
            redis_manager.set_value(redis_key, run_info)
            self.logger.info(f"保存运行信息: {run_info}")
            
            # 关闭Redis连接
            redis_manager.close()
        except Exception as e:
            self.logger.error(f"保存运行信息失败: {e}")
    
    def get_stock_list(self):
        """从数据库获取股票列表
        
        Returns:
            list: 股票代码列表
        """
        try:
            self.logger.info("从数据库获取股票列表")
            sql = "SELECT 股票代码, 股票名称 FROM 股票基本信息"
            result = self.db.query(sql)
            
            if not result:
                self.logger.warning("数据库中没有股票基本信息数据")
                return []
            
            stock_list = [item['股票代码'] for item in result]
            self.logger.info(f"获取到 {len(stock_list)} 只股票")
            return stock_list
        except Exception as e:
            self.logger.error(f"获取股票列表失败: {e}")
            return []
    
    def get_last_update_date(self, table_name, stock_code):
        """获取指定股票在指定表中的最后更新日期
        
        Args:
            table_name (str): 表名
            stock_code (str): 股票代码
            
        Returns:
            str: 最后更新日期，格式为YYYYMMDD，如果没有数据则返回None
        """
        try:
            sql = f"SELECT MAX(日期) as last_date FROM \"{table_name}\" WHERE 股票代码 = %s"
            result = self.db.query(sql, (stock_code,))
            
            if result and result[0]['last_date']:
                last_date = result[0]['last_date']
                return last_date.strftime("%Y%m%d")
            return None
        except Exception as e:
            self.logger.error(f"获取{stock_code}在{table_name}表中的最后更新日期失败: {e}")
            return None
    
    def create_tables_if_not_exist(self):
        """创建数据表（如果不存在）"""
        try:
            # 创建不复权数据表
            self.logger.info("创建不复权数据表（如果不存在）")
            sql_no_adjust = """
            CREATE TABLE IF NOT EXISTS public."股票历史行情_不复权"
            (
                "股票代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
                "日期" date NOT NULL,
                "开盘" double precision,
                "收盘" double precision,
                "最高" double precision,
                "最低" double precision,
                "成交量" numeric(38,0),
                "成交额" numeric(38,0),
                "振幅" double precision,
                "涨跌幅" double precision,
                "涨跌额" double precision,
                "换手率" double precision,
                CONSTRAINT "股票历史行情_不复权_pkey" PRIMARY KEY ("股票代码", "日期")
            ) PARTITION BY HASH ("股票代码")
            """
            self.db.execute(sql_no_adjust)

            # 创建不复权数据表的分区
            for i in range(16):
                partition_sql_no_adjust = f"""
                CREATE TABLE IF NOT EXISTS public."股票历史行情_不复权_{i}" PARTITION OF public."股票历史行情_不复权"
                    FOR VALUES WITH (modulus 16, remainder {i})
                """
                self.db.execute(partition_sql_no_adjust)
            
            # 创建后复权数据表
            self.logger.info("创建后复权数据表（如果不存在）")
            sql_hfq = """
            CREATE TABLE IF NOT EXISTS public."股票历史行情_后复权"
            (
                "股票代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
                "日期" date NOT NULL,
                "开盘" double precision,
                "收盘" double precision,
                "最高" double precision,
                "最低" double precision,
                "成交量" numeric(38,0),
                "成交额" numeric(38,0),
                "振幅" double precision,
                "涨跌幅" double precision,
                "涨跌额" double precision,
                "换手率" double precision,
                CONSTRAINT "股票历史行情_后复权_pkey" PRIMARY KEY ("股票代码", "日期")
            ) PARTITION BY HASH ("股票代码")
            """
            self.db.execute(sql_hfq)

            # 创建后复权数据表的分区
            for i in range(16):
                partition_sql_hfq = f"""
                CREATE TABLE IF NOT EXISTS public."股票历史行情_后复权_{i}" PARTITION OF public."股票历史行情_后复权"
                    FOR VALUES WITH (modulus 16, remainder {i})
                """
                self.db.execute(partition_sql_hfq)
            
            # 创建索引
            self.logger.info("创建索引（如果不存在）")
            index_sqls = [
                "CREATE INDEX IF NOT EXISTS idx_no_adjust_date ON \"股票历史行情_不复权\" (\"日期\")",
                "CREATE INDEX IF NOT EXISTS idx_hfq_date ON \"股票历史行情_后复权\" (\"日期\")"
            ]
            for sql in index_sqls:
                self.db.execute(sql)
                
            self.logger.info("数据表和索引创建完成")
        except Exception as e:
            self.logger.error(f"创建数据表失败: {e}")
    
    def fetch_stock_history(self, stock_code, start_date, end_date, adjust=""):
        """获取单只股票的历史行情数据
        
        Args:
            stock_code (str): 股票代码
            start_date (str): 开始日期，格式为YYYYMMDD
            end_date (str): 结束日期，格式为YYYYMMDD
            adjust (str, optional): 复权类型，""为不复权，"hfq"为后复权
            
        Returns:
            pandas.DataFrame: 历史行情数据
        """
        import requests
        from requests.exceptions import ConnectionError, Timeout, RequestException
        import random
        
        # 定义重试参数
        max_retries = 3
        base_delay = 2  # 基础延时秒数
        max_delay = 30  # 最大延时秒数
        
        # 根据股票代码判断市场
        market = self._get_stock_market(stock_code)
        
        # 定义接口列表，按优先级排序
        interfaces = [
            ('stock_zh_a_hist', lambda: ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start_date, end_date=end_date, adjust=adjust)),
            ('stock_zh_a_daily', lambda: ak.stock_zh_a_daily(symbol=f"{market}{stock_code}", start_date=start_date, end_date=end_date, adjust=adjust)),
            ('stock_zh_a_hist_tx', lambda: ak.stock_zh_a_hist_tx(symbol=f"{market}{stock_code}", start_date=start_date, end_date=end_date, adjust=adjust))
        ]
        
        for interface_name, interface_func in interfaces:
            for retry in range(max_retries):
                try:
                    # 添加随机延时，避免频繁请求
                    if retry > 0:
                        delay = min(base_delay * (2 ** retry) + random.uniform(0, 1), max_delay)
                        self.logger.info(f"股票{stock_code}使用{interface_name}接口第{retry+1}次重试，延时{delay:.2f}秒")
                        time.sleep(delay)
                    
                    # 调用接口获取数据
                    df = interface_func()
                    
                    if df is not None and not df.empty:
                        # 根据接口类型处理数据格式
                        if interface_name == 'stock_zh_a_hist':
                            # 东财接口，直接返回
                            df["股票代码"] = stock_code
                            return df
                        elif interface_name == 'stock_zh_a_daily':
                            # 新浪接口，需要转换列名
                            df.rename(columns={
                                "date": "日期",
                                "open": "开盘",
                                "high": "最高",
                                "low": "最低",
                                "close": "收盘",
                                "volume": "成交量",
                                "amount": "成交额",
                                "turnover": "换手率"
                            }, inplace=True)
                            
                            # 新浪接口的成交量单位是股，需要转换为手（除以100）
                            if "成交量" in df.columns:
                                df["成交量"] = df["成交量"].apply(lambda x: x / 100 if pd.notna(x) else x)
                            
                            # 添加缺失的列
                            if "振幅" not in df.columns:
                                df["振幅"] = ((df["最高"] - df["最低"]) / df["收盘"].shift(1)) * 100
                            if "涨跌幅" not in df.columns:
                                df["涨跌幅"] = ((df["收盘"] - df["收盘"].shift(1)) / df["收盘"].shift(1)) * 100
                            if "涨跌额" not in df.columns:
                                df["涨跌额"] = df["收盘"] - df["收盘"].shift(1)
                            
                            df["股票代码"] = stock_code
                            return df
                        elif interface_name == 'stock_zh_a_hist_tx':
                            # 腾讯接口，需要转换列名
                            df.rename(columns={
                                "date": "日期",
                                "open": "开盘",
                                "close": "收盘",
                                "high": "最高",
                                "low": "最低",
                                "amount": "成交量"  # 腾讯接口的amount实际是成交量（手）
                            }, inplace=True)
                            
                            # 添加缺失的列
                            if "成交额" not in df.columns:
                                # 估算成交额（成交量*收盘价*100）作为近似值
                                df["成交额"] = df["成交量"] * df["收盘"] * 100
                            
                            if "振幅" not in df.columns:
                                df["振幅"] = ((df["最高"] - df["最低"]) / df["收盘"].shift(1)) * 100
                            if "涨跌幅" not in df.columns:
                                df["涨跌幅"] = ((df["收盘"] - df["收盘"].shift(1)) / df["收盘"].shift(1)) * 100
                            if "涨跌额" not in df.columns:
                                df["涨跌额"] = df["收盘"] - df["收盘"].shift(1)
                            if "换手率" not in df.columns:
                                df["换手率"] = np.nan  # 腾讯接口没有换手率数据
                            
                            df["股票代码"] = stock_code
                            return df
                    
                    # 如果数据为空，尝试下一个接口
                    break
                    
                except (ConnectionError, Timeout, RequestException) as e:
                    # 网络相关错误，进行重试
                    if "Connection aborted" in str(e) or "Remote end closed connection" in str(e):
                        self.logger.warning(f"股票{stock_code}使用{interface_name}接口遇到连接问题: {e}，第{retry+1}/{max_retries}次重试")
                        if retry == max_retries - 1:
                            self.logger.error(f"股票{stock_code}使用{interface_name}接口重试{max_retries}次后仍然失败，尝试下一个接口")
                            break
                        continue
                    else:
                        # 其他网络错误也进行重试
                        self.logger.warning(f"股票{stock_code}使用{interface_name}接口遇到网络错误: {e}，第{retry+1}/{max_retries}次重试")
                        if retry == max_retries - 1:
                            self.logger.error(f"股票{stock_code}使用{interface_name}接口重试{max_retries}次后仍然失败，尝试下一个接口")
                            break
                        continue
                except Exception as e:
                    # 其他异常，记录并尝试下一个接口
                    self.logger.debug(f"股票{stock_code}使用{interface_name}接口失败: {e}，尝试下一个接口")
                    break
        
        # 所有接口都失败
        self.logger.warning(f"股票{stock_code}所有接口都失败，无法获取历史数据")
        return None
            
    def _get_stock_market(self, stock_code):
        """根据股票代码判断市场
        
        Args:
            stock_code (str): 股票代码
            
        Returns:
            str: 市场标识，'sh'表示上海，'sz'表示深圳，'bj'表示北京
        """
        if stock_code.startswith(('6')):  # 包含6、900开头的股票（688被6覆盖）
            return 'sh'
        elif stock_code.startswith(('0', '3', '2')):  # 深圳：0、3、2开头
            return 'sz'
        elif stock_code.startswith(('4', '8', '9')):  # 北京：4、8、9开头
            return 'bj'
        else:
            self.logger.warning(f"无法识别股票代码{stock_code}的市场，默认使用上海市场")
            return 'sh'    

    def fetch_latest_data(self):
        """获取最新一个交易日的所有股票数据（使用stock_zh_a_spot_em接口）
        
        Returns:
            pandas.DataFrame: 最新行情数据
        """
        import requests
        from requests.exceptions import ConnectionError, Timeout, RequestException
        import random
        
        # 定义重试参数
        max_retries = 3
        base_delay = 2  # 基础延时秒数
        max_delay = 30  # 最大延时秒数
        
        for retry in range(max_retries):
            try:
                # 添加随机延时，避免频繁请求
                if retry > 0:
                    delay = min(base_delay * (2 ** retry) + random.uniform(0, 1), max_delay)
                    self.logger.info(f"获取最新行情数据第{retry+1}次重试，延时{delay:.2f}秒")
                    time.sleep(delay)
                
                self.logger.info("获取最新一个交易日的所有股票数据")
                df = ak.stock_zh_a_spot_em()
                
                if df is None or df.empty:
                    self.logger.warning("获取最新行情数据为空")
                    if retry == max_retries - 1:
                        return None
                    continue
                
                # 清洗数据，要求流通市值不为空
                df = df[df["流通市值"].notna()]
                
                # 转换列名
                df.rename(columns={
                    "代码": "股票代码",
                    "今开": "开盘",
                    "最新价": "收盘",
                    "最高": "最高",
                    "最低": "最低",
                    "成交量": "成交量",
                    "成交额": "成交额",
                    "振幅": "振幅",
                    "涨跌幅": "涨跌幅",
                    "涨跌额": "涨跌额",
                    "换手率": "换手率"
                }, inplace=True)
                
                # 添加日期列
                df["日期"] = pd.to_datetime(self.last_trading_day)
                
                # 选择需要的列
                columns = ["股票代码", "日期", "开盘", "收盘", "最高", "最低", "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率"]
                df = df[columns]
                
                self.logger.info(f"获取到{len(df)}只股票的最新行情数据")
                return df
                
            except (ConnectionError, Timeout, RequestException) as e:
                # 网络相关错误，进行重试
                if "Connection aborted" in str(e) or "Remote end closed connection" in str(e):
                    self.logger.warning(f"获取最新行情数据遇到连接问题: {e}，第{retry+1}/{max_retries}次重试")
                    if retry == max_retries - 1:
                        self.logger.error(f"获取最新行情数据重试{max_retries}次后仍然失败")
                        return None
                    continue
                else:
                    # 其他网络错误也进行重试
                    self.logger.warning(f"获取最新行情数据遇到网络错误: {e}，第{retry+1}/{max_retries}次重试")
                    if retry == max_retries - 1:
                        self.logger.error(f"获取最新行情数据重试{max_retries}次后仍然失败")
                        return None
                    continue
            except Exception as e:
                self.logger.error(f"获取最新行情数据异常: {e}")
                if retry == max_retries - 1:
                    return None
                continue
        
        return None
    
    def save_to_database_with_pool(self, df, table_name):
        """使用连接池将数据保存到数据库
        
        Args:
            df (pandas.DataFrame): 要保存的数据
            table_name (str): 表名
            
        Returns:
            bool: 是否保存成功
        """
        if df is None or df.empty:
            return False
        
        try:
            # 准备数据
            records = df.to_dict('records')
            
            # 构建SQL语句
            columns = ["股票代码", "日期", "开盘", "收盘", "最高", "最低", "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率"]
            placeholders = ", ".join([f"%({col})s" for col in columns])
            columns_str = ", ".join([f"\"{col}\"" for col in columns])
            
            sql = f"""
            INSERT INTO "{table_name}" ({columns_str})
            VALUES ({placeholders})
            ON CONFLICT ("股票代码", "日期")
            DO UPDATE SET 
                "开盘" = EXCLUDED."开盘",
                "收盘" = EXCLUDED."收盘",
                "最高" = EXCLUDED."最高",
                "最低" = EXCLUDED."最低",
                "成交量" = EXCLUDED."成交量",
                "成交额" = EXCLUDED."成交额",
                "振幅" = EXCLUDED."振幅",
                "涨跌幅" = EXCLUDED."涨跌幅",
                "涨跌额" = EXCLUDED."涨跌额",
                "换手率" = EXCLUDED."换手率"
            """
            
            # 使用PostgreSQLManager的连接池执行批量插入
            return self.db.insert_df(table_name, df, conflict_columns=["股票代码", "日期"], 
                                    update_columns=["开盘", "收盘", "最高", "最低", "成交量", "成交额", 
                                                  "振幅", "涨跌幅", "涨跌额", "换手率"])
        except Exception as e:
            self.logger.error(f"保存数据到{table_name}表失败: {e}")
            return False
    
    def save_to_database(self, df, table_name):
        """将数据保存到数据库
        
        Args:
            df (pandas.DataFrame): 要保存的数据
            table_name (str): 表名
            
        Returns:
            bool: 是否保存成功
        """
        if df is None or df.empty:
            self.logger.warning(f"没有数据需要保存到{table_name}")
            return False
        
        try:
            # 准备数据
            records = df.to_dict('records')
            
            # 构建SQL语句
            columns = ["股票代码", "日期", "开盘", "收盘", "最高", "最低", "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率"]
            placeholders = ", ".join([f"%({col})s" for col in columns])
            columns_str = ", ".join([f"\"{col}\"" for col in columns])
            
            sql = f"""
            INSERT INTO "{table_name}" ({columns_str})
            VALUES ({placeholders})
            ON CONFLICT ("股票代码", "日期")
            DO UPDATE SET 
                "开盘" = EXCLUDED."开盘",
                "收盘" = EXCLUDED."收盘",
                "最高" = EXCLUDED."最高",
                "最低" = EXCLUDED."最低",
                "成交量" = EXCLUDED."成交量",
                "成交额" = EXCLUDED."成交额",
                "振幅" = EXCLUDED."振幅",
                "涨跌幅" = EXCLUDED."涨跌幅",
                "涨跌额" = EXCLUDED."涨跌额",
                "换手率" = EXCLUDED."换手率"
            """
            
            # 执行批量插入
            with self.db.conn.cursor() as cursor:
                psycopg2.extras.execute_batch(cursor, sql, records, page_size=1000)
            self.db.conn.commit()
            
            return True
        except Exception as e:
            self.db.conn.rollback()
            self.logger.error(f"保存数据到{table_name}表失败: {e}")
            return False
    
    def update_stock_data(self, stock_code):
        """更新单只股票的历史行情数据
        
        Args:
            stock_code (str): 股票代码
            
        Returns:
            bool: 是否更新成功
        """
        try:
            # 确保最后交易日已设置
            if not self.last_trading_day or not self.previous_trading_day:
                return False
                
            # 将交易日转换为YYYYMMDD格式
            last_trading_day_str = pd.to_datetime(self.last_trading_day).strftime("%Y%m%d")
            previous_trading_day_str = pd.to_datetime(self.previous_trading_day).strftime("%Y%m%d")
            
            # 获取不复权数据的最后更新日期
            last_no_adjust_date = self.get_last_update_date("股票历史行情_不复权", stock_code)
            start_date_no_adjust = self.start_date
            
            # 获取后复权数据的最后更新日期
            last_hfq_date = self.get_last_update_date("股票历史行情_后复权", stock_code)
            start_date_hfq = self.start_date
            
            # 如果有历史数据，则根据上次运行情况决定起始日期
            if last_no_adjust_date:
                # 如果上次在交易时间运行，则需要更新包括最后日期的数据
                if self.last_run_in_trading_time and last_no_adjust_date == previous_trading_day_str:
                    start_date_no_adjust = previous_trading_day_str
                else:
                    # 正常情况，从最后一天的下一天开始更新
                    last_date = datetime.datetime.strptime(last_no_adjust_date, "%Y%m%d")
                    start_date_no_adjust = (last_date + datetime.timedelta(days=1)).strftime("%Y%m%d")
            
            if last_hfq_date:
                # 后复权数据也需要考虑上次运行情况
                if self.last_run_in_trading_time and last_hfq_date == previous_trading_day_str:
                    start_date_hfq = previous_trading_day_str
                else:
                    last_date = datetime.datetime.strptime(last_hfq_date, "%Y%m%d")
                    start_date_hfq = (last_date + datetime.timedelta(days=1)).strftime("%Y%m%d")
            
            # 检查是否需要更新后复权数据
            need_update_hfq = start_date_hfq <= last_trading_day_str
            if last_hfq_date and last_hfq_date >= last_trading_day_str and not self.last_run_in_trading_time:
                need_update_hfq = False
            
            # 检查是否需要更新不复权数据
            need_update_no_adjust = start_date_no_adjust <= last_trading_day_str
            if last_no_adjust_date and last_no_adjust_date >= last_trading_day_str and not self.last_run_in_trading_time:
                need_update_no_adjust = False
            
            # 如果两种数据都不需要更新，则跳过该股票
            if not need_update_hfq and not need_update_no_adjust:
                return True
            
            # 对于不复权数据，如果起始日期在前一个交易日之后或等于它，则直接通过update_latest_data更新
            use_latest_data_only = False
            if need_update_no_adjust and start_date_no_adjust >= previous_trading_day_str:
                use_latest_data_only = True
                # 不在这里更新，而是在run方法中统一通过update_latest_data更新
                need_update_no_adjust = False
            
            # 更新后复权数据
            if need_update_hfq:
                hfq_data = self.fetch_stock_history(stock_code, start_date_hfq, last_trading_day_str, adjust="hfq")
                if hfq_data is not None and not hfq_data.empty:
                    self.save_to_database_with_pool(hfq_data, "股票历史行情_后复权")
            
            # 更新不复权数据（如果不是只使用最新数据）
            if need_update_no_adjust and not use_latest_data_only:
                no_adjust_data = self.fetch_stock_history(stock_code, start_date_no_adjust, last_trading_day_str, adjust="")
                if no_adjust_data is not None and not no_adjust_data.empty:
                    self.save_to_database_with_pool(no_adjust_data, "股票历史行情_不复权")
            
            return True
        except Exception as e:
            return False
    
    def update_latest_data(self):
        """更新最新一个交易日的数据（使用stock_zh_a_spot_em接口）
        
        Returns:
            bool: 是否更新成功
        """
        try:
            # 获取最新行情数据
            latest_data = self.fetch_latest_data()
            if latest_data is None or latest_data.empty:
                self.logger.warning("没有获取到最新行情数据，跳过更新")
                return False
            
            # 保存到不复权数据表
            self.logger.info("保存最新行情数据到不复权数据表")
            return self.save_to_database_with_pool(latest_data, "股票历史行情_不复权")
        except Exception as e:
            self.logger.error(f"更新最新行情数据失败: {e}")
            return False
    
    def run(self, limit=None):
        """运行数据更新流程

        Args:
            limit (int, optional): 限制处理的股票数量，用于测试。默认为None，表示处理所有股票。
        """
        try:
            self.logger.info("开始运行股票历史行情数据更新流程")
            
            # 创建数据表（如果不存在）
            self.create_tables_if_not_exist()
            
            # 获取股票列表
            stock_list = self.get_stock_list()
            if not stock_list:
                self.logger.error("没有获取到股票列表，无法更新数据")
                return
            
            # 如果设置了limit，则只选择部分股票用于调试
            if limit is not None and isinstance(limit, int) and limit > 0:
                stock_list = stock_list[:limit]
                self.logger.info(f"调试模式：仅处理前 {limit} 只股票")

            # 更新历史数据（使用并行处理提高效率）
            self.logger.info(f"开始更新{len(stock_list)}只股票的历史行情数据")
            success_count = 0
            failed_count = 0
            
            # 使用线程池并行处理（降低并发数以减少被封IP的风险）
            max_workers = min(3, len(stock_list))  # 最多3个线程，降低并发以避免IP被封
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                future_to_stock = {executor.submit(self.update_stock_data, stock_code): stock_code for stock_code in stock_list}
                
                # 处理结果
                for future in tqdm(concurrent.futures.as_completed(future_to_stock), total=len(stock_list), desc="更新历史数据"):
                    stock_code = future_to_stock[future]
                    try:
                        if future.result():
                            success_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        self.logger.error(f"更新{stock_code}时发生异常: {e}")
                        failed_count += 1
            
            self.logger.info(f"历史数据更新完成，成功更新{success_count}/{len(stock_list)}只股票，失败{failed_count}只")
            
            # 更新最新一个交易日的数据
            # 无论是否在交易时间，都更新最新数据，这样可以确保那些起始日期在previous_trading_day之后的股票得到更新
            if self.last_trading_day:
                self.logger.info("开始更新最新一个交易日的数据")
                if self.update_latest_data():
                    self.logger.info("最新交易日数据更新成功")
                else:
                    self.logger.warning("最新交易日数据更新失败")
            
            # 保存本次运行信息
            self._save_run_info()
            
            self.logger.info("股票历史行情数据更新流程完成")
        except Exception as e:
            self.logger.error(f"运行股票历史行情数据更新流程失败: {e}")
        finally:
            # 关闭数据库连接
            self.db.close()
            # 关闭网络会话
            if hasattr(self, 'session') and self.session:
                self.session.close()


def main():
    """主函数"""
    # 记录开始时间
    start_time = time.time()
    
    # 初始化日志
    logger_manager = LoggerManager()
    logger = logger_manager.get_logger("stock_historical")
    
    try:
        logger.info("=== 开始运行股票历史行情数据获取程序 ===")
        
        # 创建StockHistoricalData实例并运行
        data_fetcher = StockHistoricalData()
        data_fetcher.run()
        
        # 记录结束时间和运行时间
        end_time = time.time()
        run_time = end_time - start_time
        logger.info(f"程序运行完成，耗时: {run_time:.2f}秒")
        logger.info("=== 股票历史行情数据获取程序运行结束 ===")
    except Exception as e:
        logger.error(f"程序运行异常: {e}")
        logger.error("=== 股票历史行情数据获取程序异常终止 ===")


if __name__ == "__main__":
    main()