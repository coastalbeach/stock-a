#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
批量股票历史数据获取模块

基于akshare的stock_zh_a_hist函数，实现大量股票的批量获取和增量更新
支持多线程并发、断点续传、错误重试等功能
"""

import os
import sys
import time
import datetime
import pandas as pd
import numpy as np
import threading
import concurrent.futures
from queue import Queue, Empty
from pathlib import Path
from tqdm import tqdm
import logging
import json
from typing import List, Dict, Optional, Tuple

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入项目模块
from utils.logger import LoggerManager
from utils.config_loader import load_connection_config
from db import PostgreSQLManager, RedisManager

# 导入AKShare
import akshare as ak


class BatchHistoricalFetcher:
    """批量股票历史数据获取器
    
    功能特性：
    1. 基于akshare.stock_zh_a_hist函数获取数据
    2. 支持多线程并发获取
    3. 智能增量更新（只获取缺失的数据）
    4. 断点续传功能
    5. 错误重试机制
    6. Redis缓存优化
    7. 进度监控和日志记录
    """
    
    def __init__(self, max_workers=8, batch_size=50, retry_times=3):
        """初始化批量获取器
        
        Args:
            max_workers (int): 最大工作线程数
            batch_size (int): 每批处理的股票数量
            retry_times (int): 失败重试次数
        """
        # 初始化日志
        self.logger = self._init_logger()
        self.logger.info("初始化批量股票历史数据获取器")
        
        # 配置参数
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.retry_times = retry_times
        
        # 初始化数据库连接
        self.db = PostgreSQLManager(use_pool=True, max_connections=max_workers + 2)
        self.redis = RedisManager()
        
        # 数据获取参数
        self.start_date = "20050104"  # 默认起始日期
        self.end_date = datetime.datetime.now().strftime("%Y%m%d")
        
        # 状态跟踪
        self.total_stocks = 0
        self.completed_stocks = 0
        self.failed_stocks = []
        self.progress_lock = threading.Lock()
        
        # 断点续传文件
        self.checkpoint_file = os.path.join(project_root, "data", "batch_checkpoint.json")
        
        # 确保数据目录存在
        os.makedirs(os.path.dirname(self.checkpoint_file), exist_ok=True)
        
    def _init_logger(self):
        """初始化日志记录器"""
        logger_manager = LoggerManager()
        logger = logger_manager.get_logger("batch_historical_fetcher")
        return logger
    
    def get_stock_list(self) -> List[str]:
        """从数据库获取股票列表
        
        Returns:
            List[str]: 股票代码列表
        """
        try:
            self.logger.info("从数据库获取股票列表")
            sql = "SELECT 股票代码 FROM 股票基本信息 ORDER BY 股票代码"
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
    
    def get_missing_data_info(self, stock_code: str) -> Dict[str, Optional[str]]:
        """获取股票缺失数据信息
        
        Args:
            stock_code (str): 股票代码
            
        Returns:
            Dict[str, Optional[str]]: 包含不复权和后复权表的最后更新日期
        """
        info = {
            "不复权": None,
            "后复权": None
        }
        
        tables = ["股票历史行情_不复权", "股票历史行情_后复权"]
        table_keys = ["不复权", "后复权"]
        
        for table, key in zip(tables, table_keys):
            try:
                sql = f"SELECT MAX(日期) as last_date FROM \"{table}\" WHERE 股票代码 = %s"
                result = self.db.query(sql, (stock_code,))
                
                if result and result[0]['last_date']:
                    last_date = result[0]['last_date']
                    info[key] = last_date.strftime("%Y%m%d")
                else:
                    info[key] = None
            except Exception as e:
                self.logger.error(f"获取{stock_code}在{table}表中的最后更新日期失败: {e}")
                info[key] = None
        
        return info
    
    def calculate_date_range(self, last_update_date: Optional[str]) -> Tuple[str, str]:
        """计算需要获取的日期范围
        
        Args:
            last_update_date (Optional[str]): 最后更新日期，格式YYYYMMDD
            
        Returns:
            Tuple[str, str]: (开始日期, 结束日期)
        """
        if last_update_date is None:
            # 没有历史数据，从默认起始日期开始
            return self.start_date, self.end_date
        else:
            # 有历史数据，从下一天开始
            last_date = datetime.datetime.strptime(last_update_date, "%Y%m%d")
            next_date = last_date + datetime.timedelta(days=1)
            start_date = next_date.strftime("%Y%m%d")
            
            # 如果开始日期已经超过结束日期，说明数据已经是最新的
            if start_date > self.end_date:
                return None, None
            
            return start_date, self.end_date
    
    def fetch_stock_data(self, stock_code: str, start_date: str, end_date: str, adjust: str = "") -> Optional[pd.DataFrame]:
        """获取单只股票的历史数据
        
        Args:
            stock_code (str): 股票代码
            start_date (str): 开始日期，格式YYYYMMDD
            end_date (str): 结束日期，格式YYYYMMDD
            adjust (str): 复权类型，""=不复权，"hfq"=后复权
            
        Returns:
            Optional[pd.DataFrame]: 股票数据，失败时返回None
        """
        try:
            # 使用akshare获取数据
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            
            if df.empty:
                self.logger.warning(f"股票{stock_code}在{start_date}到{end_date}期间没有数据")
                return None
            
            # 数据预处理
            df = self._preprocess_data(df, stock_code)
            return df
            
        except Exception as e:
            self.logger.error(f"获取股票{stock_code}数据失败: {e}")
            return None
    
    def _preprocess_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """预处理股票数据
        
        Args:
            df (pd.DataFrame): 原始数据
            stock_code (str): 股票代码
            
        Returns:
            pd.DataFrame: 处理后的数据
        """
        # 确保股票代码列存在
        if '股票代码' not in df.columns:
            df['股票代码'] = stock_code
        
        # 确保日期格式正确
        if '日期' in df.columns:
            df['日期'] = pd.to_datetime(df['日期']).dt.date
        
        # 数值列转换
        numeric_columns = ['开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 重新排列列顺序
        expected_columns = [
            '日期', '股票代码', '开盘', '收盘', '最高', '最低', 
            '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率'
        ]
        
        # 只保留存在的列
        available_columns = [col for col in expected_columns if col in df.columns]
        df = df[available_columns]
        
        return df
    
    def save_data_to_db(self, df: pd.DataFrame, table_name: str) -> bool:
        """保存数据到数据库
        
        Args:
            df (pd.DataFrame): 要保存的数据
            table_name (str): 目标表名
            
        Returns:
            bool: 保存是否成功
        """
        try:
            if df.empty:
                return True
            
            # 使用UPSERT操作，避免重复数据
            primary_keys = ['股票代码', '日期']
            success = self.db.upsert_from_df(
                df=df,
                table_name=table_name,
                primary_keys=primary_keys
            )
            
            if success:
                self.logger.debug(f"成功保存{len(df)}条数据到{table_name}表")
            else:
                self.logger.error(f"保存数据到{table_name}表失败")
            
            return success
            
        except Exception as e:
            self.logger.error(f"保存数据到{table_name}表异常: {e}")
            return False
    
    def process_single_stock(self, stock_code: str) -> Dict[str, bool]:
        """处理单只股票的数据获取
        
        Args:
            stock_code (str): 股票代码
            
        Returns:
            Dict[str, bool]: 处理结果，包含不复权和后复权的成功状态
        """
        result = {"不复权": False, "后复权": False}
        
        try:
            # 获取缺失数据信息
            missing_info = self.get_missing_data_info(stock_code)
            
            # 处理不复权数据
            last_date_no_adjust = missing_info["不复权"]
            start_date, end_date = self.calculate_date_range(last_date_no_adjust)
            
            if start_date and end_date:
                df_no_adjust = self.fetch_stock_data(stock_code, start_date, end_date, "")
                if df_no_adjust is not None:
                    success = self.save_data_to_db(df_no_adjust, "股票历史行情_不复权")
                    result["不复权"] = success
                    if success:
                        self.logger.debug(f"股票{stock_code}不复权数据更新成功，新增{len(df_no_adjust)}条记录")
                else:
                    result["不复权"] = True  # 没有新数据也算成功
            else:
                result["不复权"] = True  # 数据已是最新
            
            # 处理后复权数据
            last_date_hfq = missing_info["后复权"]
            start_date, end_date = self.calculate_date_range(last_date_hfq)
            
            if start_date and end_date:
                df_hfq = self.fetch_stock_data(stock_code, start_date, end_date, "hfq")
                if df_hfq is not None:
                    success = self.save_data_to_db(df_hfq, "股票历史行情_后复权")
                    result["后复权"] = success
                    if success:
                        self.logger.debug(f"股票{stock_code}后复权数据更新成功，新增{len(df_hfq)}条记录")
                else:
                    result["后复权"] = True  # 没有新数据也算成功
            else:
                result["后复权"] = True  # 数据已是最新
            
            # 添加短暂延迟，避免API请求过于频繁
            time.sleep(0.1)
            
        except Exception as e:
            self.logger.error(f"处理股票{stock_code}时发生异常: {e}")
        
        return result
    
    def worker_thread(self, stock_queue: Queue, progress_bar: tqdm):
        """工作线程函数
        
        Args:
            stock_queue (Queue): 股票代码队列
            progress_bar (tqdm): 进度条对象
        """
        while True:
            try:
                # 从队列获取股票代码
                stock_code = stock_queue.get(timeout=1)
                
                # 处理股票数据
                retry_count = 0
                success = False
                
                while retry_count < self.retry_times and not success:
                    try:
                        result = self.process_single_stock(stock_code)
                        
                        # 检查是否成功
                        if result["不复权"] and result["后复权"]:
                            success = True
                            with self.progress_lock:
                                self.completed_stocks += 1
                        else:
                            retry_count += 1
                            if retry_count < self.retry_times:
                                time.sleep(retry_count * 2)  # 指数退避
                    
                    except Exception as e:
                        retry_count += 1
                        self.logger.error(f"处理股票{stock_code}第{retry_count}次尝试失败: {e}")
                        if retry_count < self.retry_times:
                            time.sleep(retry_count * 2)
                
                # 如果最终失败，记录到失败列表
                if not success:
                    with self.progress_lock:
                        self.failed_stocks.append(stock_code)
                        self.logger.error(f"股票{stock_code}处理失败，已重试{self.retry_times}次")
                
                # 更新进度
                progress_bar.update(1)
                
                # 标记任务完成
                stock_queue.task_done()
                
            except Empty:
                # 队列为空，退出线程
                break
            except Exception as e:
                self.logger.error(f"工作线程异常: {e}")
                break
    
    def save_checkpoint(self, completed_stocks: List[str], failed_stocks: List[str]):
        """保存断点信息
        
        Args:
            completed_stocks (List[str]): 已完成的股票列表
            failed_stocks (List[str]): 失败的股票列表
        """
        try:
            checkpoint_data = {
                "timestamp": datetime.datetime.now().isoformat(),
                "completed_stocks": completed_stocks,
                "failed_stocks": failed_stocks,
                "total_stocks": self.total_stocks,
                "completed_count": len(completed_stocks)
            }
            
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"断点信息已保存到 {self.checkpoint_file}")
        except Exception as e:
            self.logger.error(f"保存断点信息失败: {e}")
    
    def load_checkpoint(self) -> Optional[Dict]:
        """加载断点信息
        
        Returns:
            Optional[Dict]: 断点信息，如果文件不存在则返回None
        """
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint_data = json.load(f)
                self.logger.info(f"加载断点信息: {checkpoint_data['timestamp']}")
                return checkpoint_data
            return None
        except Exception as e:
            self.logger.error(f"加载断点信息失败: {e}")
            return None
    
    def run_batch_update(self, stock_list: Optional[List[str]] = None, use_checkpoint: bool = True) -> Dict[str, any]:
        """运行批量更新
        
        Args:
            stock_list (Optional[List[str]]): 指定的股票列表，如果为None则获取所有股票
            use_checkpoint (bool): 是否使用断点续传
            
        Returns:
            Dict[str, any]: 执行结果统计
        """
        start_time = datetime.datetime.now()
        self.logger.info("开始批量股票历史数据更新")
        
        try:
            # 获取股票列表
            if stock_list is None:
                stock_list = self.get_stock_list()
            
            if not stock_list:
                self.logger.error("没有获取到股票列表")
                return {"success": False, "message": "没有获取到股票列表"}
            
            # 处理断点续传
            completed_stocks = []
            if use_checkpoint:
                checkpoint = self.load_checkpoint()
                if checkpoint:
                    completed_stocks = checkpoint.get("completed_stocks", [])
                    # 过滤掉已完成的股票
                    stock_list = [stock for stock in stock_list if stock not in completed_stocks]
                    self.logger.info(f"断点续传: 跳过{len(completed_stocks)}只已完成的股票，剩余{len(stock_list)}只")
            
            self.total_stocks = len(stock_list)
            self.completed_stocks = 0
            self.failed_stocks = []
            
            if self.total_stocks == 0:
                self.logger.info("所有股票数据已是最新，无需更新")
                return {
                    "success": True,
                    "total_stocks": len(completed_stocks),
                    "completed_stocks": len(completed_stocks),
                    "failed_stocks": 0,
                    "message": "所有股票数据已是最新"
                }
            
            # 创建股票队列
            stock_queue = Queue()
            for stock_code in stock_list:
                stock_queue.put(stock_code)
            
            # 创建进度条
            progress_bar = tqdm(
                total=self.total_stocks,
                desc="批量更新股票数据",
                unit="只",
                ncols=100
            )
            
            # 启动工作线程
            threads = []
            for i in range(self.max_workers):
                thread = threading.Thread(
                    target=self.worker_thread,
                    args=(stock_queue, progress_bar),
                    name=f"Worker-{i+1}"
                )
                thread.daemon = True
                thread.start()
                threads.append(thread)
            
            # 等待所有任务完成
            stock_queue.join()
            
            # 等待所有线程结束
            for thread in threads:
                thread.join(timeout=5)
            
            progress_bar.close()
            
            # 保存最终断点信息
            all_completed = completed_stocks + [stock for stock in stock_list if stock not in self.failed_stocks]
            self.save_checkpoint(all_completed, self.failed_stocks)
            
            # 计算执行时间
            end_time = datetime.datetime.now()
            duration = end_time - start_time
            
            # 生成执行报告
            result = {
                "success": True,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration.total_seconds(),
                "total_stocks": self.total_stocks + len(completed_stocks),
                "completed_stocks": self.completed_stocks + len(completed_stocks),
                "failed_stocks": len(self.failed_stocks),
                "failed_stock_list": self.failed_stocks,
                "success_rate": (self.completed_stocks / self.total_stocks * 100) if self.total_stocks > 0 else 100
            }
            
            self.logger.info(f"批量更新完成: 总计{result['total_stocks']}只股票，成功{result['completed_stocks']}只，失败{result['failed_stocks']}只，耗时{duration}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"批量更新过程中发生异常: {e}")
            return {"success": False, "message": str(e)}
        
        finally:
            # 清理资源
            self.cleanup()
    
    def cleanup(self):
        """清理资源"""
        try:
            if hasattr(self, 'db') and self.db:
                self.db.close()
            if hasattr(self, 'redis') and self.redis:
                self.redis.close()
            self.logger.info("资源清理完成")
        except Exception as e:
            self.logger.error(f"资源清理失败: {e}")


def main():
    """主函数 - 示例用法"""
    # 创建批量获取器
    fetcher = BatchHistoricalFetcher(
        max_workers=8,  # 8个工作线程
        batch_size=50,  # 每批50只股票
        retry_times=3   # 失败重试3次
    )
    
    # 运行批量更新
    result = fetcher.run_batch_update(use_checkpoint=True)
    
    # 打印结果
    if result["success"]:
        print(f"\n批量更新成功完成!")
        print(f"总股票数: {result['total_stocks']}")
        print(f"成功更新: {result['completed_stocks']}")
        print(f"失败数量: {result['failed_stocks']}")
        print(f"成功率: {result['success_rate']:.2f}%")
        print(f"耗时: {result['duration_seconds']:.2f}秒")
        
        if result['failed_stock_list']:
            print(f"\n失败的股票: {', '.join(result['failed_stock_list'])}")
    else:
        print(f"批量更新失败: {result['message']}")


if __name__ == "__main__":
    main()