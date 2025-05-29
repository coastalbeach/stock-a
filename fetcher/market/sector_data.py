#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
行业历史行情数据获取模块

获取所有行业板块的历史行情数据，并存储到PostgreSQL数据库中。
"""

import os
import sys
import time
import pandas as pd
import akshare as ak
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent.parent) # fetcher/market/sector_data.py -> stock-a
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入数据存储模块
try:
    from db import PostgreSQLManager
except ImportError:
    print("错误：无法导入 PostgreSQLManager。请确保 data.storage.postgresql_manager.py 文件存在且路径正确。")
    sys.exit(1)

# 导入日志模块 (如果需要)
# from utils.logger import logger

class SectorDataFetcher:
    """行业历史行情数据获取与存储类"""

    def __init__(self, max_workers=4):
        """初始化数据库连接和线程池"""
        try:
            self.pg_manager = PostgreSQLManager()
            print("数据库连接成功。")
        except Exception as e:
            print(f"数据库连接失败: {e}")
            # logger.error(f"数据库连接失败: {e}") # 如果使用日志
            sys.exit(1)
        self.max_workers = max_workers
        self.table_name = "行业历史行情"
        self._create_table()

    def _create_table(self):
        """创建存储行业历史行情的数据库表（如果不存在）"""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS "{self.table_name}" (
            "行业名称" VARCHAR(100) NOT NULL,
            "日期" DATE NOT NULL,
            "开盘" FLOAT,
            "收盘" FLOAT,
            "最高" FLOAT,
            "最低" FLOAT,
            "成交量" numeric(38,0),  -- 注意：AKShare返回的是手，需要乘以100
            "成交额" numeric(38,0),
            "振幅" FLOAT,
            "涨跌幅" FLOAT,
            "涨跌额" FLOAT,
            "换手率" FLOAT,
            PRIMARY KEY ("行业名称", "日期")
        );
        """
        try:
            self.pg_manager.execute(create_table_sql)
            # 创建索引提高查询效率
            index_sql = f'CREATE INDEX IF NOT EXISTS idx_{self.table_name}_行业名称_日期 ON "{self.table_name}" ("行业名称", "日期");'
            self.pg_manager.execute(index_sql)
            print(f'数据表 "{self.table_name}" 创建或已存在。')
            # logger.info(f'数据表 "{self.table_name}" 创建或已存在。') # 如果使用日志
        except Exception as e:
            print(f'创建数据表 "{self.table_name}" 失败: {e}')
            # logger.error(f'创建数据表 "{self.table_name}" 失败: {e}') # 如果使用日志
            # sys.exit(1) # 根据需要决定是否在表创建失败时退出

    def get_all_sector_names(self):
        """获取所有行业板块的名称列表

        优先从数据库 '行业板块' 表获取，如果失败则通过 AKShare API 获取。

        Returns:
            list: 包含所有行业行业名称的列表，如果获取失败则返回空列表。
        """
        print("开始获取所有行业行业名称...")
        try:
            # 尝试从数据库获取
            query = 'SELECT DISTINCT "行业名称" FROM "行业板块"'
            result = self.pg_manager.query(query)
            if result:
                sector_names = [row[0] for row in result]
                print(f"成功从数据库获取 {len(sector_names)} 个行业行业名称。")
                return sector_names
            else:
                print("数据库中未找到行业板块数据，尝试从 AKShare 获取...")
        except Exception as db_e:
            print(f"从数据库获取行业行业名称时出错: {db_e}，尝试从 AKShare 获取...")

        # 如果数据库获取失败，则从 AKShare 获取
        try:
            sector_df = ak.stock_board_industry_name_em()
            if not sector_df.empty and '行业名称' in sector_df.columns:
                sector_names = sector_df['行业名称'].tolist()
                print(f"成功从 AKShare 获取 {len(sector_names)} 个行业行业名称。")
                # logger.info(f"成功获取 {len(sector_names)} 个行业行业名称。")
                # 可选：将获取到的数据存入 '行业板块' 表，如果该表存在的话
                # self.save_sector_names_to_db(sector_df) # 需要实现这个方法
                return sector_names
            else:
                print("未能从AKShare获取有效的行业板块列表。")
                # logger.warning("未能从AKShare获取有效的行业板块列表。")
                return []
        except Exception as api_e:
            print(f"通过 AKShare 获取行业行业名称列表时出错: {api_e}")
            # logger.error(f"获取行业行业名称列表时出错: {api_e}")
            return []

    def fetch_sector_history(self, sector_name, period="日k", start_date="19900101", end_date="20991231"):
        """获取单个行业板块的历史行情数据

        Args:
            sector_name (str): 行业行业名称。
            period (str): 数据周期，'daily', 'weekly', 'monthly'。
            start_date (str): 开始日期 (YYYYMMDD)。
            end_date (str): 结束日期 (YYYYMMDD)。

        Returns:
            pandas.DataFrame: 包含该板块历史行情数据的DataFrame，失败则返回空DataFrame。
        """
        try:
            # print(f"开始获取板块 '{sector_name}' 的历史行情数据 ({start_date} - {end_date})...")
            # 使用东方财富数据源获取板块历史行情
            # 注意：period 参数应为 "日k", "周k", "月k"
            hist_df = ak.stock_board_industry_hist_em(
                symbol=sector_name,
                period=period, # 确保传入的是 "日k", "周k", "月k"
                start_date=start_date,
                end_date=end_date,
                adjust="" # 不复权
            )

            if hist_df.empty:
                # print(f"板块 '{sector_name}' 未获取到历史行情数据。")
                # logger.warning(f"板块 '{sector_name}' 未获取到历史行情数据。")
                return pd.DataFrame()

            # 数据清洗和处理
            hist_df['日期'] = pd.to_datetime(hist_df['日期']).dt.date
            hist_df['行业名称'] = sector_name
            # 将成交量从“手”转换为“股”
            if '成交量' in hist_df.columns:
                hist_df['成交量'] = hist_df['成交量'] * 100

            # 选择并重排需要的列以匹配数据库表结构
            required_columns = ["行业名称", "日期", "开盘", "收盘", "最高", "最低", "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率"]
            hist_df = hist_df[required_columns]

            # print(f"成功获取板块 '{sector_name}' 的 {len(hist_df)} 条历史行情数据。")
            # logger.debug(f"成功获取板块 '{sector_name}' 的 {len(hist_df)} 条历史行情数据。")
            return hist_df

        except Exception as e:
            print(f"获取板块 '{sector_name}' 历史行情数据时出错: {e}")
            # logger.error(f"获取板块 '{sector_name}' 历史行情数据时出错: {e}")
            # 网络错误或API限制可能导致获取失败，返回空DataFrame让上层处理
            return pd.DataFrame()

    def save_sector_history(self, df):
        """将获取到的板块历史行情数据保存到PostgreSQL数据库

        Args:
            df (pandas.DataFrame): 包含板块历史行情数据的DataFrame。

        Returns:
            bool: 保存是否成功。
        """
        if df.empty:
            return False

        sector_name = df['行业名称'].iloc[0]
        try:
            # 使用 PostgreSQLManager 的 insert_df 方法进行高效插入和冲突处理
            # conflict_columns 指定主键列，update_columns 指定冲突时需要更新的列
            conflict_columns = ['行业名称', '日期']
            update_columns = [col for col in df.columns if col not in conflict_columns]

            self.pg_manager.insert_df(self.table_name, df, conflict_columns=conflict_columns, update_columns=update_columns)
            # print(f"成功保存板块 '{sector_name}' 的 {len(df)} 条历史行情数据到数据库。")
            # logger.debug(f"成功保存板块 '{sector_name}' 的 {len(df)} 条历史行情数据到数据库。")
            return True
        except Exception as e:
            print(f"保存板块 '{sector_name}' 历史行情数据到数据库时出错: {e}")
            # logger.error(f"保存板块 '{sector_name}' 历史行情数据到数据库时出错: {e}")
            return False

    def _get_latest_date_for_sector(self, sector_name):
        """查询指定板块在数据库中的最新日期"""
        query = f'SELECT MAX("日期") FROM "{self.table_name}" WHERE "行业名称" = %s'
        try:
            result = self.pg_manager.query(query, (sector_name,))
            if result and result[0] and result[0][0]:
                return result[0][0]
        except Exception as e:
            print(f"查询板块 '{sector_name}' 最新日期时出错: {e}")
            # logger.error(f"查询板块 '{sector_name}' 最新日期时出错: {e}")
        return None

    def update_all_sector_history(self, start_date="19900101", end_date="20991231"):
        """获取并更新所有行业板块的历史行情数据（增量更新）"""
        sector_names = self.get_all_sector_names()
        if not sector_names:
            print("无法获取行业板块列表，更新中止。")
            # logger.error("无法获取行业板块列表，更新中止。")
            return

        print(f"开始更新 {len(sector_names)} 个行业板块的历史行情数据...")
        # logger.info(f"开始更新 {len(sector_names)} 个行业板块的历史行情数据...")

        successful_updates = 0
        failed_sectors = []

        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for name in sector_names:
                # 获取该板块的最新日期
                latest_db_date = self._get_latest_date_for_sector(name)
                fetch_start_date = start_date # 默认起始日期

                if latest_db_date:
                    # 如果数据库中有数据，则从最新日期的下一天开始获取
                    next_day = latest_db_date + timedelta(days=1)
                    fetch_start_date = next_day.strftime('%Y%m%d')
                    # print(f"板块 '{name}' 已有数据至 {latest_db_date}, 将从 {fetch_start_date} 开始获取增量数据。")
                    # logger.info(f"板块 '{name}' 已有数据至 {latest_db_date}, 将从 {fetch_start_date} 开始获取增量数据。")
                # 如果计算出的起始日期晚于结束日期，则跳过此板块
                elif fetch_start_date > end_date:
                    # print(f"板块 '{name}' 的数据已是最新 ({latest_db_date})，无需更新。")
                    # logger.info(f"板块 '{name}' 的数据已是最新 ({latest_db_date})，无需更新。")
                    continue                    
                else:
                     print(f"板块 '{name}' 在数据库中无历史数据，将从 {fetch_start_date} 开始获取全部数据。")
                    # logger.info(f"板块 '{name}' 在数据库中无历史数据，将从 {fetch_start_date} 开始获取全部数据。")

                # 提交任务到线程池
                # 提交任务到线程池并保存对应的行业名称
                futures[executor.submit(
                    self.fetch_sector_history,
                    name,
                    period="日k",
                    start_date=fetch_start_date,
                    end_date=end_date
                )] = name

            if not futures:
                print("所有板块数据均已是最新，无需更新。")
                # logger.info("所有板块数据均已是最新，无需更新。")
                return

            for future in tqdm(as_completed(futures), total=len(futures), desc="获取板块历史数据"):
                sector_name = futures[future]
                try:
                    hist_df = future.result()
                    if not hist_df.empty:
                        if self.save_sector_history(hist_df):
                            successful_updates += 1
                        else:
                            print(f"板块 '{sector_name}' 数据保存失败。")
                            # logger.warning(f"板块 '{sector_name}' 数据保存失败。")
                            failed_sectors.append(sector_name)
                    else:
                        # 如果获取的DataFrame为空，说明数据获取失败或该时间段无数据
                        print(f"板块 '{sector_name}' 未获取到历史行情数据或该时间段无数据。")
                        # logger.info(f"板块 '{sector_name}' 未获取到历史行情数据或该时间段无数据。")
                        failed_sectors.append(sector_name) # 将其视为获取失败
                except Exception as e:
                    print(f"处理板块 '{sector_name}' 时发生意外错误: {e}")
                    # logger.error(f"处理板块 '{sector_name}' 时发生意外错误: {e}")
                    failed_sectors.append(sector_name)
                # 添加延时防止触发反爬虫机制
                time.sleep(0.1) # 可根据实际情况调整延时

        print(f"\n所有行业历史行情数据更新完成。")
        total_sectors = len(sector_names)
        print(f"总计 {total_sectors} 个板块，成功更新 {successful_updates} 个板块。")
        if failed_sectors:
            print(f"以下 {len(failed_sectors)} 个板块未能成功获取或更新数据: {', '.join(failed_sectors)}")
            # logger.warning(f"以下 {len(failed_sectors)} 个板块未能成功获取或更新数据: {', '.join(failed_sectors)}")
        elif successful_updates == total_sectors:
            print("所有板块均已成功更新或数据已是最新。")
            # logger.info("所有板块均已成功更新或数据已是最新。")
        else:
            # This case might occur if some sectors were skipped (e.g., data already up-to-date)
            # and no new failures occurred, but not all sectors were 'successfully_updated' in this run.
            print(f"{successful_updates} 个板块数据已更新，其余板块数据已是最新或无需更新。")

# 主程序入口，用于测试或直接运行脚本
if __name__ == "__main__":
    fetcher = SectorDataFetcher(max_workers=8) # 可以调整并发数

    # 示例：更新所有板块从2023年至今的数据
    # today = datetime.date.today().strftime('%Y%m%d')
    # fetcher.update_all_sector_history(start_date="20230101", end_date=today)

    # 示例：更新所有板块的全部历史数据（可能非常耗时）
    print("开始获取并更新所有行业板块的全部历史行情数据...")
    fetcher.update_all_sector_history()
    print("所有行业板块历史数据更新任务结束。")

    # 关闭数据库连接
    fetcher.pg_manager.close()
    print("数据库连接已关闭。")