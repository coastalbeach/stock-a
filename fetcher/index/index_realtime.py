#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
指数实时行情数据获取模块

获取主要指数的实时行情数据，包括上证系列指数、深证系列指数、沪深重要指数、中证系列指数等
实时数据存储在Redis中，历史数据存储在PostgreSQL中
"""

import os
import sys
import yaml
import json
import datetime
import pandas as pd
import akshare as ak
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent.parent) 
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入数据存储模块
from db import PostgreSQLManager, RedisManager


class IndexRealtime:
    """指数实时行情数据获取类"""
    
    def __init__(self):
        """初始化"""
        self.pg_manager = PostgreSQLManager()
        self.redis_manager = RedisManager()
        self.config = self._load_config()
        self.max_workers = 4  # 并行获取数据的最大线程数
        
        # 指数类型列表
        self.index_types = [
            "沪深重要指数", 
            "上证系列指数", 
            "深证系列指数", 
            "中证系列指数",
            "指数成份"
        ]
        
        # Redis键前缀和过期时间
        self.redis_key_prefix = "指数实时行情:"
        self.redis_expire = 60  # 60秒过期，保证数据新鲜度
        
    def _load_config(self):
        """加载数据库配置"""
        config_path = os.path.join(project_root, 'config', 'connection.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    
    def create_tables(self):
        """创建指数实时行情数据表"""
        try:
            # 创建指数实时行情数据表
            self.pg_manager.execute("""
            CREATE TABLE IF NOT EXISTS "指数实时行情" (
                "序号" INTEGER,
                "代码" VARCHAR(10) NOT NULL,
                "名称" VARCHAR(50) NOT NULL,
                "最新价" FLOAT,
                "涨跌额" FLOAT,
                "涨跌幅" FLOAT,
                "成交量" FLOAT,
                "成交额" FLOAT,
                "振幅" FLOAT,
                "最高" FLOAT,
                "最低" FLOAT,
                "今开" FLOAT,
                "昨收" FLOAT,
                "量比" FLOAT,
                "指数类型" VARCHAR(20) NOT NULL,
                "更新时间" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY ("代码", "指数类型")
            );
            """)
            
            # 创建更新时间索引，提高查询效率
            self.pg_manager.execute("""
            CREATE INDEX IF NOT EXISTS "idx_指数实时行情_更新时间" ON "指数实时行情" ("更新时间");
            """)
            
            print("指数实时行情数据表创建成功")
            return True
        except Exception as e:
            print(f"创建指数实时行情数据表失败: {e}")
            return False
    
    def fetch_index_realtime(self, index_type):
        """获取指定类型的指数实时行情数据
        
        Args:
            index_type (str): 指数类型，可选值为："沪深重要指数", "上证系列指数", "深证系列指数", "中证系列指数", "指数成份"
            
        Returns:
            pandas.DataFrame: 指数实时行情数据
        """
        try:
            print(f"获取 {index_type} 实时行情数据...")
            
            # 使用akshare获取指数实时行情数据
            df = ak.stock_zh_index_spot_em(symbol=index_type)
            
            # 如果数据为空，返回空DataFrame
            if df.empty:
                print(f"{index_type} 没有获取到数据")
                return pd.DataFrame()
            
            # 添加指数类型列
            df['指数类型'] = index_type
            
            # 添加更新时间列
            df['更新时间'] = datetime.datetime.now()
            
            print(f"{index_type} 获取到 {len(df)} 条数据")
            return df
        except Exception as e:
            print(f"获取 {index_type} 实时行情数据失败: {e}")
            # 网络错误需要抛出以便外层重试
            if "Connection" in str(e) or "Timeout" in str(e) or "timeout" in str(e):
                raise e
            return pd.DataFrame()
    
    def save_index_data(self, df):
        """保存指数实时行情数据到Redis和PostgreSQL
        
        Args:
            df (pandas.DataFrame): 指数实时行情数据
            
        Returns:
            bool: 保存是否成功
        """
        if df.empty:
            return False
        
        try:
            # 1. 保存到Redis (实时数据)
            redis_success = self.save_to_redis(df)
            
            # 2. 保存到PostgreSQL (历史数据)
            pg_success = self.save_to_postgresql(df)
            
            if redis_success and pg_success:
                print(f"成功保存 {len(df)} 条指数实时行情数据到Redis和PostgreSQL")
            elif redis_success:
                print(f"成功保存 {len(df)} 条指数实时行情数据到Redis，但PostgreSQL保存失败")
            elif pg_success:
                print(f"成功保存 {len(df)} 条指数实时行情数据到PostgreSQL，但Redis保存失败")
            else:
                print("保存指数实时行情数据失败")
            
            return redis_success or pg_success
        except Exception as e:
            print(f"保存指数实时行情数据失败: {e}")
            return False
    
    def save_to_redis(self, df):
        """保存指数实时行情数据到Redis
        
        Args:
            df (pandas.DataFrame): 指数实时行情数据
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 获取指数类型
            index_type = df['指数类型'].iloc[0] if not df.empty else ""
            
            # 创建Redis键
            redis_key = f"{self.redis_key_prefix}{index_type}"
            
            # 遍历DataFrame，将每行数据保存到Redis
            for _, row in df.iterrows():
                # 使用指数代码作为哈希表的字段名
                index_code = row['代码']
                
                # 将行数据转换为字典，并将日期时间转换为字符串
                row_dict = row.to_dict()
                if '更新时间' in row_dict and isinstance(row_dict['更新时间'], datetime.datetime):
                    row_dict['更新时间'] = row_dict['更新时间'].strftime('%Y-%m-%d %H:%M:%S')
                
                # 将字典转换为JSON字符串
                json_data = json.dumps(row_dict, ensure_ascii=False)
                
                # 保存到Redis哈希表
                self.redis_manager.set_hash(redis_key, index_code, json_data, expire=self.redis_expire)
            
            # 设置一个索引键，用于存储所有指数类型
            index_types_key = f"{self.redis_key_prefix}types"
            self.redis_manager.set_hash(index_types_key, index_type, "1", expire=self.redis_expire*2)
            
            print(f"成功保存 {len(df)} 条指数实时行情数据到Redis")
            return True
        except Exception as e:
            print(f"保存指数实时行情数据到Redis失败: {e}")
            return False
    
    def save_to_postgresql(self, df):
        """保存指数实时行情数据到PostgreSQL
        
        Args:
            df (pandas.DataFrame): 指数实时行情数据
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 使用insert_df方法批量插入数据
            # 定义冲突时需要更新的列
            conflict_columns = ["代码", "指数类型"]
            update_columns = [
                "序号", "名称", "最新价", "涨跌额", "涨跌幅", "成交量", "成交额", 
                "振幅", "最高", "最低", "今开", "昨收", "量比", "更新时间"
            ]
            
            # 批量插入数据，冲突时更新
            result = self.pg_manager.insert_df(
                df=df,
                table_name="指数实时行情",
                conflict_columns=conflict_columns,
                update_columns=update_columns
            )
            
            if result:
                print(f"成功保存 {len(df)} 条指数实时行情数据到PostgreSQL")
            else:
                print("保存指数实时行情数据到PostgreSQL失败")
            
            return result
        except Exception as e:
            print(f"保存指数实时行情数据到PostgreSQL失败: {e}")
            return False
    
    def update_all_index_realtime(self):
        """更新所有类型的指数实时行情数据"""
        try:
            # 确保数据表已创建
            self.create_tables()
            
            # 使用线程池并行获取不同类型的指数数据
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任务
                future_to_index = {executor.submit(self.fetch_index_realtime, index_type): index_type 
                                  for index_type in self.index_types}
                
                # 处理任务结果
                for future in as_completed(future_to_index):
                    index_type = future_to_index[future]
                    try:
                        df = future.result()
                        if not df.empty:
                            self.save_index_data(df)
                    except Exception as e:
                        print(f"处理 {index_type} 数据时出错: {e}")
            
            print("所有指数实时行情数据更新完成")
            return True
        except Exception as e:
            print(f"更新指数实时行情数据失败: {e}")
            return False
    
    def get_index_realtime(self, index_type=None, index_code=None, use_redis=True):
        """查询指数实时行情数据
        
        Args:
            index_type (str, optional): 指数类型
            index_code (str, optional): 指数代码
            use_redis (bool, optional): 是否优先使用Redis查询，默认为True
            
        Returns:
            pandas.DataFrame: 查询结果
        """
        try:
            # 优先从Redis获取数据
            if use_redis:
                redis_data = self.get_from_redis(index_type, index_code)
                if not redis_data.empty:
                    return redis_data
                print("Redis中没有找到数据，将从PostgreSQL获取")
            
            # 如果Redis中没有数据或指定不使用Redis，则从PostgreSQL获取
            return self.get_from_postgresql(index_type, index_code)
        except Exception as e:
            print(f"查询指数实时行情数据失败: {e}")
            return pd.DataFrame()
    
    def get_from_redis(self, index_type=None, index_code=None):
        """从Redis获取指数实时行情数据
        
        Args:
            index_type (str, optional): 指数类型
            index_code (str, optional): 指数代码
            
        Returns:
            pandas.DataFrame: 查询结果
        """
        try:
            data_list = []
            
            # 如果指定了指数代码和类型
            if index_type and index_code:
                redis_key = f"{self.redis_key_prefix}{index_type}"
                json_data = self.redis_manager.get_hash(redis_key, index_code)
                if json_data:
                    # 解析JSON数据
                    try:
                        row_dict = json.loads(json_data)
                        data_list.append(row_dict)
                    except:
                        pass
            
            # 如果只指定了指数类型
            elif index_type:
                redis_key = f"{self.redis_key_prefix}{index_type}"
                hash_data = self.redis_manager.get_all_hash(redis_key)
                for _, json_data in hash_data.items():
                    try:
                        row_dict = json.loads(json_data)
                        data_list.append(row_dict)
                    except:
                        continue
            
            # 如果只指定了指数代码
            elif index_code:
                # 获取所有指数类型
                index_types_key = f"{self.redis_key_prefix}types"
                types_hash = self.redis_manager.get_all_hash(index_types_key)
                
                # 遍历所有指数类型
                for index_type in types_hash.keys():
                    redis_key = f"{self.redis_key_prefix}{index_type}"
                    json_data = self.redis_manager.get_hash(redis_key, index_code)
                    if json_data:
                        try:
                            row_dict = json.loads(json_data)
                            data_list.append(row_dict)
                        except:
                            continue
            
            # 如果没有指定任何条件，获取所有数据
            else:
                # 获取所有指数类型
                index_types_key = f"{self.redis_key_prefix}types"
                types_hash = self.redis_manager.get_all_hash(index_types_key)
                
                # 遍历所有指数类型
                for index_type in types_hash.keys():
                    redis_key = f"{self.redis_key_prefix}{index_type}"
                    hash_data = self.redis_manager.get_all_hash(redis_key)
                    for _, json_data in hash_data.items():
                        try:
                            row_dict = json.loads(json_data)
                            data_list.append(row_dict)
                        except:
                            continue
            
            # 将数据列表转换为DataFrame
            if data_list:
                df = pd.DataFrame(data_list)
                
                # 转换更新时间列为datetime类型
                if '更新时间' in df.columns:
                    df['更新时间'] = pd.to_datetime(df['更新时间'])
                
                # 按指数类型和序号排序
                if '指数类型' in df.columns and '序号' in df.columns:
                    df = df.sort_values(by=['指数类型', '序号'])
                
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            print(f"从Redis获取指数实时行情数据失败: {e}")
            return pd.DataFrame()
    
    def get_from_postgresql(self, index_type=None, index_code=None):
        """从PostgreSQL获取指数实时行情数据
        
        Args:
            index_type (str, optional): 指数类型
            index_code (str, optional): 指数代码
            
        Returns:
            pandas.DataFrame: 查询结果
        """
        try:
            # 构建SQL查询条件
            conditions = []
            params = []
            
            if index_type:
                conditions.append("\"指数类型\" = %s")
                params.append(index_type)
            
            if index_code:
                conditions.append("\"代码\" = %s")
                params.append(index_code)
            
            # 构建完整SQL
            sql = "SELECT * FROM \"指数实时行情\""            
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            
            # 添加排序
            sql += " ORDER BY \"指数类型\", \"序号\""            
            
            # 执行查询
            result = self.pg_manager.query(sql, tuple(params) if params else None)
            
            # 将结果转换为DataFrame
            if result:
                columns = [
                    "序号", "代码", "名称", "最新价", "涨跌额", "涨跌幅", "成交量", "成交额", 
                    "振幅", "最高", "最低", "今开", "昨收", "量比", "指数类型", "更新时间"
                ]
                df = pd.DataFrame(result, columns=columns)
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            print(f"从PostgreSQL获取指数实时行情数据失败: {e}")
            return pd.DataFrame()


# 测试代码
if __name__ == "__main__":
    # 创建指数实时行情数据获取对象
    index_realtime = IndexRealtime()
    
    # 更新所有指数实时行情数据
    index_realtime.update_all_index_realtime()
    
    print("\n" + "-"*50)
    print("测试从Redis获取数据")
    print("-"*50)
    
    # 查询上证系列指数的实时行情数据（从Redis获取）
    print("\n1. 从Redis获取上证系列指数的实时行情数据:")
    df = index_realtime.get_index_realtime(index_type="上证系列指数", use_redis=True)
    if not df.empty:
        print(f"获取到 {len(df)} 条数据")
        print(df.head())
    
    # 查询特定指数的实时行情数据（从Redis获取）
    print("\n2. 从Redis获取特定指数(000001)的实时行情数据:")
    df = index_realtime.get_index_realtime(index_code="000001", use_redis=True)
    if not df.empty:
        print(f"获取到 {len(df)} 条数据")
        print(df.head())
    
    print("\n" + "-"*50)
    print("测试从PostgreSQL获取数据")
    print("-"*50)
    
    # 查询上证系列指数的实时行情数据（从PostgreSQL获取）
    print("\n1. 从PostgreSQL获取上证系列指数的实时行情数据:")
    df = index_realtime.get_index_realtime(index_type="上证系列指数", use_redis=False)
    if not df.empty:
        print(f"获取到 {len(df)} 条数据")
        print(df.head())
    
    # 查询特定指数的实时行情数据（从PostgreSQL获取）
    print("\n2. 从PostgreSQL获取特定指数(000001)的实时行情数据:")
    df = index_realtime.get_index_realtime(index_code="000001", use_redis=False)
    if not df.empty:
        print(f"获取到 {len(df)} 条数据")
        print(df.head())
    
    # 关闭Redis连接
    index_realtime.redis_manager.close()